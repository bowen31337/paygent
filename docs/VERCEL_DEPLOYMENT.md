# Vercel Deployment Guide for Paygent

This guide explains how to deploy the Paygent AI-Powered Payment Orchestration Platform to Vercel.

## Overview

Paygent uses Vercel's Python runtime to deploy a FastAPI application as serverless functions. The deployment includes:

- **FastAPI Application**: ASGI app deployed via `api/index.py`
- **Python 3.11 Runtime**: Latest stable Python version
- **Vercel Postgres**: Serverless PostgreSQL database
- **Vercel KV**: Redis-compatible cache layer
- **Vercel Blob**: File storage for agent logs

## Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **Vercel CLI**: Install globally
   ```bash
   npm install -g vercel
   ```
3. **GitHub Repository**: Push your code to GitHub (optional but recommended)

## Deployment Configuration

### Files Created

1. **api/index.py**: Vercel serverless function entry point
   - Imports FastAPI app from `src/main.py`
   - Exports ASGI handler for Vercel

2. **vercel.json**: Vercel deployment configuration
   - Python 3.11 runtime
   - Routes for API endpoints
   - Memory: 1024 MB
   - Max duration: 60 seconds

3. **requirements.txt**: Python dependencies (229 packages)
   - Generated from `pyproject.toml`
   - Includes all production dependencies

4. **.vercelignore**: Files to exclude from deployment
   - Development files, tests, docs
   - Reduces deployment size

### Environment Variables

Configure these in Vercel Project Settings > Environment Variables:

#### Required

- `ANTHROPIC_API_KEY`: Anthropic API key for Claude Sonnet 4
- `CRONOS_RPC_URL`: Cronos RPC endpoint (testnet or mainnet)
- `JWT_SECRET`: Secret key for JWT authentication

#### Vercel Infrastructure (Auto-configured)

When you provision these services, Vercel auto-sets these variables:

**Vercel Postgres:**
- `POSTGRES_URL`: Connection string with pooling
- `POSTGRES_PRISMA_URL`: Prisma-compatible connection
- `POSTGRES_URL_NON_POOLING`: Direct connection
- `POSTGRES_USER`: Database user
- `POSTGRES_HOST`: Database host
- `POSTGRES_PASSWORD`: Database password
- `POSTGRES_DATABASE`: Database name

**Vercel KV:**
- `KV_URL`: Redis connection URL
- `KV_REST_API_URL`: REST API endpoint
- `KV_REST_API_TOKEN`: REST API token
- `KV_REST_API_READ_ONLY_TOKEN`: Read-only token

**Vercel Blob:**
- `BLOB_READ_WRITE_TOKEN`: Blob storage token

#### Optional

- `OPENAI_API_KEY`: Fallback to GPT-4 (if Claude unavailable)
- `X402_FACILITATOR_URL`: x402 payment facilitator endpoint
- `LOG_LEVEL`: Logging level (default: INFO)
- `CORS_ORIGINS`: Comma-separated list of allowed origins

## Deployment Steps

### 1. Link Project to Vercel

```bash
vercel link
```

This creates a `.vercel` directory and links your project to Vercel.

### 2. Provision Vercel Services

In the Vercel Dashboard:

1. **Postgres Database**:
   - Go to Storage > Postgres
   - Click "Create Database"
   - Choose region (same as app)
   - Copy connection strings

2. **KV Store**:
   - Go to Storage > KV
   - Click "Create Database"
   - Choose region
   - Copy connection strings

3. **Blob Storage**:
   - Go to Storage > Blob
   - Click "Create Store"
   - Copy token

### 3. Set Environment Variables

In Vercel Dashboard > Project Settings > Environment Variables:

1. Add all required variables from above
2. Select appropriate environments (Production, Preview, Development)
3. Save changes

### 4. Run Database Migrations

Connect to your Vercel Postgres database and run migrations:

```bash
# Using the Vercel Postgres connection string
export DATABASE_URL="postgres://..."

# Run Alembic migrations
uv run alembic upgrade head
```

Or use Vercel's Postgres dashboard to run SQL directly:

```sql
-- Run migrations via Vercel dashboard
-- See alembic/versions/ for SQL scripts
```

### 5. Deploy to Vercel

```bash
# Deploy to preview (for testing)
vercel

# Deploy to production
vercel --prod
```

Vercel will:
1. Build your Python application
2. Install dependencies from `requirements.txt`
3. Deploy as serverless functions
4. Provide a URL (e.g., `https://paygent.vercel.app`)

### 6. Verify Deployment

Test the deployed application:

```bash
# Health check
curl https://your-app.vercel.app/health

# API docs
curl https://your-app.vercel.app/docs

# OpenAPI spec
curl https://your-app.vercel.app/openapi.json
```

Expected response from health check:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "production"
}
```

## Testing Locally with Vercel Dev

To test your deployment locally before pushing:

```bash
# Install dependencies
npm install -g vercel

# Start local development server
vercel dev

# Test endpoints
curl http://localhost:3000/health
```

This simulates the Vercel environment locally.

## Performance Optimization

### Cold Starts

Serverless functions have cold starts. To minimize:

1. **Keep bundle small**: `.vercelignore` excludes unnecessary files
2. **Optimize imports**: Lazy load heavy dependencies
3. **Use provisioned concurrency** (Vercel Hobby+): Keeps functions warm

### Database Connection Pooling

Vercel Postgres includes built-in connection pooling. The `POSTGRES_URL` uses pooling automatically.

### Cache Layer

Vercel KV provides low-latency caching:
- Service discovery cache: 5-minute TTL
- Session state: 1-hour TTL
- Rate limiting: 1-minute TTL

### Monitoring

Access Vercel Analytics:
- Function execution time
- Error rates
- Request volume
- Cold start frequency

## Troubleshooting

### Build Failures

**Issue**: Build fails during dependency installation

**Solution**:
- Check `requirements.txt` is up to date
- Verify all dependencies are compatible with Python 3.11
- Check Vercel build logs for specific errors

### Runtime Errors

**Issue**: Function crashes on execution

**Solution**:
- Check Vercel Function Logs
- Verify environment variables are set
- Test with `vercel dev` locally first

### Database Connection Errors

**Issue**: Cannot connect to Vercel Postgres

**Solution**:
- Verify `DATABASE_URL` or `POSTGRES_URL` is set
- Check IP allowlisting (Vercel IPs are auto-whitelisted)
- Test connection string with `psql` or other client

### Timeouts

**Issue**: Functions timeout after 60 seconds

**Solution**:
- Optimize long-running operations
- Increase `maxDuration` in `vercel.json` (max 60s for Hobby)
- Consider using Vercel Cron Jobs for scheduled tasks
- Use Vercel Workflows for long-running agent execution

### Memory Limits

**Issue**: Functions run out of memory

**Solution**:
- Increase `memory` in `vercel.json` (max 1024 MB for Hobby)
- Optimize memory usage in code
- Use streaming responses for large data

## CI/CD with GitHub

### Automatic Deployments

1. Connect GitHub repository to Vercel
2. Vercel automatically deploys on push to `main` branch
3. Preview deployments for pull requests

### Environment-Specific Config

Use different environment variables per environment:

| Environment | Purpose | Auto-Deploy |
|-------------|---------|-------------|
| Production | Live site | `main` branch |
| Preview | PR reviews | Pull requests |
| Development | Testing | `dev` branch |

### Deployment Hooks

Add custom build scripts in `vercel.json`:

```json
{
  "buildCommand": "uv run alembic upgrade head && uv run pytest",
  "devCommand": "uv run uvicorn src.main:app --reload"
}
```

## Monitoring and Logging

### Vercel Dashboard

- **Functions**: View function logs and metrics
- **Storage**: Monitor Postgres, KV, and Blob usage
- **Analytics**: Track request volume and performance
- **Deployments**: View deployment history and logs

### Application Logging

The app uses Python logging. Logs appear in Vercel Function Logs:

```python
import logging
logger = logging.getLogger(__name__)
logger.info("Agent execution started")
```

### Error Tracking

Consider integrating error tracking:
- **Sentry**: Real-time error tracking
- **LogRocket**: Session replay
- **Vercel Log Drains**: Forward logs to external service

## Cost Optimization

### Vercel Pricing Tiers

| Tier | Price | Limits |
|------|-------|--------|
| Free | $0 | 100 GB bandwidth, 100 GB-hrs compute |
| Pro | $20/mo | 1 TB bandwidth, 1000 GB-hrs compute |
| Team | $60/mo | 5 TB bandwidth, unlimited projects |

### Cost-Saving Tips

1. **Optimize bundle size**: Reduces deployment time
2. **Use edge functions**: Static content served from CDN
3. **Monitor usage**: Check Vercel dashboard regularly
4. **Set budgets**: Configure cost alerts in Vercel settings

## Security Best Practices

1. **Never commit secrets**: Use environment variables
2. **Enable HTTPS**: Vercel provides automatic SSL
3. **Rate limiting**: Built-in middleware prevents abuse
4. **CORS configuration**: Restrict to allowed origins
5. **Input validation**: Pydantic models validate all inputs
6. **Database security**: Use connection pooling and prepared statements

## Next Steps

After deployment:

1. **Set up custom domain**: Vercel Dashboard > Domains
2. **Configure analytics**: Vercel Analytics or Google Analytics
3. **Set up monitoring**: Uptime monitoring and alerts
4. **Document API**: Share `/docs` URL with developers
5. **Monitor costs**: Check Vercel dashboard regularly

## Support

- **Vercel Docs**: https://vercel.com/docs
- **Vercel Status**: https://www.vercel-status.com
- **GitHub Issues**: Report bugs in repository

## Deployment Checklist

Before deploying to production:

- [ ] All tests passing locally
- [ ] Environment variables configured in Vercel
- [ ] Vercel Postgres database provisioned
- [ ] Vercel KV store provisioned
- [ ] Vercel Blob storage provisioned
- [ ] Database migrations run successfully
- [ ] Health endpoint responds correctly
- [ ] API documentation accessible
- [ ] Custom domain configured (optional)
- [ ] Monitoring and alerting set up
- [ ] Cost budget configured

## Summary

Vercel deployment provides:

✅ **Serverless Functions**: Auto-scaling Python runtime
✅ **Managed Infrastructure**: Postgres, KV, and Blob storage
✅ **Zero Configuration**: Automatic SSL and CDN
✅ **Fast Deployment**: Build and deploy in seconds
✅ **Preview URLs**: Test changes before production
✅ **GitHub Integration**: Automatic deployments on push

Your Paygent application is now ready to deploy to Vercel!
