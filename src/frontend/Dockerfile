# TruePulse Frontend - Production Dockerfile
# Multi-stage build for Static Web Apps deployment

# ============================================================================
# Stage 1: Dependencies
# ============================================================================
FROM node:20-bookworm-slim AS deps

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# ============================================================================
# Stage 2: Builder
# ============================================================================
FROM node:20-bookworm-slim AS builder

WORKDIR /app

# Copy dependencies
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build arguments for environment variables
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Build the application (static export)
RUN npm run build

# ============================================================================
# Stage 3: Production (for SWA deployment, we just need the static files)
# ============================================================================
FROM nginx:alpine AS production

# Copy static files from builder
COPY --from=builder /app/out /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
