# Storybook Deployment Options

## Option 1: Docker Compose (Simple)

Serve pre-built Storybook files using the main docker-compose setup.

### Steps:

```bash
# 1. Build Storybook
cd /workspaces/backstage-plugin-sandbox/plugins/sample-frontend
yarn build-storybook

# 2. Start the Storybook service
cd /workspaces/backstage-plugin-sandbox/.devcontainer
docker-compose --profile storybook up storybook -d

# 3. Access at http://localhost:6006
```

### Stop the service:

```bash
docker-compose --profile storybook down storybook
```

**Note:** This requires rebuilding Storybook manually each time you make changes.

---

## Option 2: Standalone Docker Image (Production)

Build a self-contained Docker image with multi-stage build.

### Steps:

```bash
# Build from the plugin directory
cd /workspaces/backstage-plugin-sandbox/plugins/sample-frontend
docker build -f Dockerfile.storybook -t sample-storybook .

# Run the container
docker run -d -p 6006:80 --name storybook sample-storybook

# Access at http://localhost:6006
```

### Stop and remove:

```bash
docker stop storybook
docker rm storybook
```

---

## Option 3: Local Development Server

Serve built Storybook locally without Docker.

### Steps:

```bash
# 1. Build Storybook
cd /workspaces/backstage-plugin-sandbox/plugins/sample-frontend
yarn build-storybook

# 2. Serve with npx
npx serve storybook-static -p 6006

# Access at http://localhost:6006
```

**Use Ctrl+C to stop.**

---

## Option 4: Live Development (Recommended for Development)

Run Storybook with hot reload for active development.

### Steps:

```bash
cd /workspaces/backstage-plugin-sandbox/plugins/sample-frontend
yarn storybook

# Access at http://localhost:6006
```

This provides instant feedback as you edit stories.

---

## Comparison

| Option                | Use Case                       | Pros                            | Cons                  |
| --------------------- | ------------------------------ | ------------------------------- | --------------------- |
| **Docker Compose**    | Quick preview of built version | Simple, integrated with dev env | Manual rebuild needed |
| **Standalone Docker** | Production, CI/CD, sharing     | Self-contained, portable        | Longer build time     |
| **Local npx serve**   | Quick local preview            | Fast, no Docker overhead        | Requires Node.js      |
| **yarn storybook**    | Active development             | Hot reload, instant feedback    | Dev server overhead   |

---

## CI/CD Integration

### Build and push to registry:

```bash
docker build -f Dockerfile.storybook -t your-registry/sample-storybook:latest .
docker push your-registry/sample-storybook:latest
```

### Deploy to Kubernetes:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: storybook
spec:
  replicas: 2
  selector:
    matchLabels:
      app: storybook
  template:
    metadata:
      labels:
        app: storybook
    spec:
      containers:
        - name: storybook
          image: your-registry/sample-storybook:latest
          ports:
            - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: storybook
spec:
  selector:
    app: storybook
  ports:
    - port: 80
      targetPort: 80
  type: LoadBalancer
```
