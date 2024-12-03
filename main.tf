# Provider configuration for AWS
provider "aws" {
  region = "eu-south-2"
}

# EC2 Instance definition with existing Security Group
resource "aws_instance" "main_api_project" {
  ami                    = "ami-01c698987a62f1cee" # If I go to AWS and "AMIs" i'll find the ami, and is asociated with the instance configuration
  instance_type          = "t3.medium"
  vpc_security_group_ids = ["sg-0ceebb5821128f97d"]  # Created security group ID (so recomended, otherwise, you can also create here your security group)

  tags = {
    Name = "Project Main API"
  }
  

  # Once the server is running, execute this commands in order to exec the program
  provisioner "remote-exec" {
    inline = [
      "sudo apt-get update -y",
      "sudo timedatectl set-timezone Europe/Madrid",

      # Install Docker
      "sudo apt-get install -y ca-certificates curl gnupg lsb-release",
      "sudo mkdir -p /etc/apt/keyrings",
      "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg",
      "echo \"deb [arch=\\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \\$(lsb_release -cs) stable\" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null",
      "sudo apt-get update -y",
      "sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",

       # Add Kubernetes repository
      "sudo apt-get install -y apt-transport-https ca-certificates curl",
      "curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -",
      "echo \"deb https://apt.kubernetes.io/ kubernetes-xenial main\" | sudo tee -a /etc/apt/sources.list.d/kubernetes.list",

      # Install Kubernetes tools
      "sudo apt-get update -y",
      "sudo apt-get install -y kubelet kubeadm kubectl",
      "sudo apt-mark hold kubelet kubeadm kubectl",

      # Disable swap (required for Kubernetes)
      "sudo swapoff -a",
      "sudo sed -i '/ swap / s/^/#/' /etc/fstab",

      # Join the Kubernetes cluster (replace <control-plane-ip> and <token> with real values)
      "sudo kubeadm join <control-plane-ip>:6443 --token <token> --discovery-token-ca-cert-hash <ca-cert-hash>"
    ]
  }

}
