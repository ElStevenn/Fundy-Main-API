### Local machine deployment

- Start minikube
```bash
    minikube start
```
- Set pod configuration (for each service as needed)
```
    kubectl apply -f deployment.yaml
    kubectl apply -f service.yaml
    kubectl apply -f secrets.yaml # If needed
```

### Server-side deployment