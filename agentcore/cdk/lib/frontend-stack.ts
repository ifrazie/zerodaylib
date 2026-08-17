import {
  CfnOutput,
  Duration,
  RemovalPolicy,
  Stack,
  type StackProps,
} from 'aws-cdk-lib';
import * as apigwv2 from 'aws-cdk-lib/aws-apigatewayv2';
import { HttpLambdaIntegration } from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';
import * as fs from 'fs';

export interface FrontendStackProps extends StackProps {
  /** Project name (for resource naming + tags). */
  readonly projectName: string;
  /**
   * Absolute path to the Next.js static export output directory
   * (`frontend/out`). Must exist at synth time (run `next build` first).
   */
  readonly frontendOutDir: string;
  /**
   * Absolute path to the API Lambda deployment zip (`dist/zdl-api-handler.zip`).
   * Produced by `backend/package_api_lambda.sh`.
   */
  readonly apiHandlerZip: string;
  /**
   * Absolute path to the shared psycopg Lambda layer zip
   * (`dist/zdl-tools-layer.zip`). Produced by `backend/package_lambda.sh --layer`.
   */
  readonly psycopgLayerZip: string;
  /**
   * Secrets Manager ARN holding the CockroachDB connection URL. The API Lambda
   * reads it at cold start (COCKROACH_SECRET_ARN). Reuse the same secret the
   * AgentCore tools Lambda uses.
   */
  readonly cockroachSecretArn: string;
}

/**
 * Hosts the ZDL Next.js dashboard as a static site on S3 + CloudFront, and the
 * FastAPI read API (`/api/*`) on API Gateway (HTTP API) + Lambda (Mangum).
 *
 * A single CloudFront distribution fronts both origins:
 *   - default behavior            → private S3 bucket (Origin Access Control)
 *   - `/api/*` behavior           → API Gateway HTTP API (no caching)
 *
 * A CloudFront Function (viewer-request) rewrites deep links / refreshes for the
 * client-routed dynamic segment `/finding/<id>` to the exported SPA shell so the
 * `/finding/[id]` route keeps working under a pure static export.
 *
 * The browser talks to `/api/*` same-origin, so no CORS round-trips are needed.
 */
export class FrontendStack extends Stack {
  public readonly distributionDomainName: string;

  constructor(scope: Construct, id: string, props: FrontendStackProps) {
    super(scope, id, props);

    const {
      projectName,
      frontendOutDir,
      apiHandlerZip,
      psycopgLayerZip,
      cockroachSecretArn,
    } = props;

    // --- Preflight checks: fail fast with actionable messages at synth time
    if (!fs.existsSync(frontendOutDir)) {
      throw new Error(
        `Frontend export not found at "${frontendOutDir}". Run \`cd frontend && npm ci && npm run build:clean\` first ` +
          `(next.config.mjs must use output: 'export').`
      );
    }
    if (!fs.existsSync(apiHandlerZip)) {
      throw new Error(
        `API Lambda zip not found at "${apiHandlerZip}". Run \`bash backend/package_api_lambda.sh\` first.`
      );
    }
    if (!fs.existsSync(psycopgLayerZip)) {
      throw new Error(
        `psycopg layer zip not found at "${psycopgLayerZip}". Run \`bash backend/package_lambda.sh --layer\` first.`
      );
    }

    // --- Static site bucket (private; served only via CloudFront OAC)
    const siteBucket = new s3.Bucket(this, 'SiteBucket', {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      versioned: true,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    // --- API Lambda (FastAPI via Mangum)
    const psycopgLayer = new lambda.LayerVersion(this, 'PsycopgLayer', {
      code: lambda.Code.fromAsset(psycopgLayerZip),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_12],
      compatibleArchitectures: [lambda.Architecture.ARM_64],
      description: 'psycopg[binary] (ARM64) + CockroachDB CA cert',
    });

    const apiFn = new lambda.Function(this, 'ApiFunction', {
      runtime: lambda.Runtime.PYTHON_3_12,
      architecture: lambda.Architecture.ARM_64,
      handler: 'api_lambda.handler',
      code: lambda.Code.fromAsset(apiHandlerZip),
      layers: [psycopgLayer],
      memorySize: 512,
      timeout: Duration.seconds(30),
      environment: {
        COCKROACH_SECRET_ARN: cockroachSecretArn,
        COCKROACH_SSLROOTCERT: '/var/task/certs/cc-ca.crt',
        // 4 AgentCore runtimes are deployed (supervisor, ingest, governance,
        // remediation); override via ZDL_AGENT_COUNT at `cdk deploy` time if
        // that ever changes without a code update here.
        ZDL_AGENT_COUNT: process.env.ZDL_AGENT_COUNT ?? '4',
        // FRONTEND_ORIGIN is added below once the distribution domain is known.
      },
      description: `${projectName} frontend read API (FastAPI/Mangum)`,
    });

    // Read the CockroachDB connection secret at cold start.
    // The provided ARN includes the 6-character random suffix Secrets Manager
    // appends, so use the complete-ARN form. This grants read on the exact
    // secret resource; the partial-ARN form would grant on a suffix-less ARN
    // that does not match the real resource, yielding AccessDeniedException.
    const cockroachSecret = secretsmanager.Secret.fromSecretCompleteArn(
      this,
      'CockroachSecret',
      cockroachSecretArn
    );
    cockroachSecret.grantRead(apiFn);

    // Invoke Bedrock Titan Text v2 for query-time embeddings (semantic memory).
    apiFn.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['bedrock:InvokeModel'],
        resources: [
          `arn:aws:bedrock:${this.region}::foundation-model/amazon.titan-embed-text-v2:0`,
        ],
      })
    );

    // --- API Gateway (HTTP API) → Lambda proxy
    const httpApi = new apigwv2.HttpApi(this, 'HttpApi', {
      apiName: `${projectName}-frontend-api`,
      // CORS is handled same-origin via CloudFront; no gateway CORS needed.
    });
    httpApi.addRoutes({
      path: '/{proxy+}',
      methods: [apigwv2.HttpMethod.ANY],
      integration: new HttpLambdaIntegration('ApiIntegration', apiFn),
    });

    // HttpApi.apiEndpoint is like https://{id}.execute-api.{region}.amazonaws.com
    const apiDomain = `${httpApi.apiId}.execute-api.${this.region}.${this.urlSuffix}`;

    // --- CloudFront Function: SPA deep-link rewrite for /finding/*
    // Rewrites requests without a file extension under /finding/ to the exported
    // shell so `/finding/<uuid>` deep links & refreshes resolve to the SPA.
    // `/api/*` and real asset requests are left untouched.
    const spaRewriteFn = new cloudfront.Function(this, 'SpaRewriteFunction', {
      code: cloudfront.FunctionCode.fromInline(`
function handler(event) {
  var request = event.request;
  var uri = request.uri;

  // Leave API calls and requests that already target a file untouched.
  if (uri.startsWith('/api/')) { return request; }
  if (uri.includes('.')) { return request; }

  // Dynamic finding detail route → exported shell (finding/_shell.html).
  if (uri === '/finding' || uri.startsWith('/finding/')) {
    request.uri = '/finding/_shell.html';
    return request;
  }

  // Directory-style requests → their index.html (Next export layout).
  if (uri.endsWith('/')) {
    request.uri = uri + 'index.html';
    return request;
  }
  request.uri = uri + '.html';
  return request;
}
`),
      comment: 'ZDL SPA deep-link rewrite (Next.js static export)',
    });

    // --- CloudFront distribution (two origins)
    const s3Origin = origins.S3BucketOrigin.withOriginAccessControl(siteBucket);

    const apiOrigin = new origins.HttpOrigin(apiDomain, {
      protocolPolicy: cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
    });

    const distribution = new cloudfront.Distribution(this, 'Distribution', {
      comment: `${projectName} dashboard`,
      defaultRootObject: 'index.html',
      defaultBehavior: {
        origin: s3Origin,
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
        functionAssociations: [
          {
            function: spaRewriteFn,
            eventType: cloudfront.FunctionEventType.VIEWER_REQUEST,
          },
        ],
      },
      additionalBehaviors: {
        'api/*': {
          origin: apiOrigin,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          originRequestPolicy:
            cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
        },
      },
    });

    // Now that the distribution domain exists, pin the API Lambda CORS origin.
    apiFn.addEnvironment(
      'FRONTEND_ORIGIN',
      `https://${distribution.distributionDomainName}`
    );

    // --- Deploy the static export to S3 + invalidate CloudFront
    new s3deploy.BucketDeployment(this, 'DeploySite', {
      sources: [s3deploy.Source.asset(frontendOutDir)],
      destinationBucket: siteBucket,
      distribution,
      distributionPaths: ['/*'],
    });

    this.distributionDomainName = distribution.distributionDomainName;

    // --- Outputs
    new CfnOutput(this, 'FrontendUrl', {
      description: 'CloudFront URL for the ZDL dashboard',
      value: `https://${distribution.distributionDomainName}`,
    });
    new CfnOutput(this, 'ApiEndpoint', {
      description: 'API Gateway HTTP API endpoint (origin behind CloudFront /api/*)',
      value: httpApi.apiEndpoint,
    });
    new CfnOutput(this, 'SiteBucketName', {
      description: 'S3 bucket hosting the static export',
      value: siteBucket.bucketName,
    });
  }
}
