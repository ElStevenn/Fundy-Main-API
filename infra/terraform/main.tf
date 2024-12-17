# Provider configuration for AWS
provider "aws" {
  region = "eu-south-2"
}

# Key Pair
resource "aws_key_pair" "instance_pub_key" {
  key_name = "instance_key_api"
  public_key = file("../../src/security/instance_key.pub")
}

# Needed role
resource "aws_iam_role" "ssm_role" {
  name = "ssm_full_acces_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "ec2.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ssm_full_access" {
  role       = aws_iam_role.ssm_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMFullAccess"
}



# Needed data form the 
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] 

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

data "aws_security_group" "paus-security-group" {
  name = "paus-security-group"
  id = "sg-0ceebb5821128f97d"
}

data "aws_iam_instance_profile" "cli_permissions" {
  name = "cli_permissions"
}

resource "aws_eip" "main_api_eip" {
  instance = aws_instance.main_api_project.id

  tags = {
    Name = "Trade Visionary Main API EIP"
  }
}

# EC2 Instance definition with existing Security Group
resource "aws_instance" "main_api_project" {
  ami                    = var.ami_id
  instance_type          = "t3.medium"
  key_name               = aws_key_pair.instance_pub_key.key_name
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [data.aws_security_group.paus-security-group.id]  

  iam_instance_profile = data.aws_iam_instance_profile.cli_permissions.name

  tags = {
    Name = "Trade Visionary Main API"
    Type = "User Handling"
  }

  root_block_device {
    volume_size           = 30
    volume_type           = "gp3"
    delete_on_termination = true
  }

  lifecycle {
    ignore_changes = [ami] # Prevent Terraform from recreating due to AMI drift
  }

  provisioner "local-exec" {
    command = <<EOT
      cd .. &&
      cd .. &&
      git add . &&
      git commit -m "${var.commit_message}" &&
      git push -u origin main
      
    EOT
  }


    connection {
      type = "ssh"
      user = "ubuntu"
      private_key = file("../../src/security/instance_key")
      host = self.public_ip
    }
  

  provisioner "file" {
    source = "/home/mrpau/Desktop/Secret_Project/other_layers/Fundy-Main-API/scripts"
    destination = "/home/ubuntu/scripts"

    connection {
      type = "ssh"
      user = "ubuntu"
      private_key = file("../../src/security/instance_key")
      host = self.public_ip
    }
  } 

  provisioner "remote-exec" {
    inline = [
      "chmod +x /home/ubuntu/scripts/*",
      "bash /home/ubuntu/scripts/CI/source.sh"
    ]
    connection {
      type        = "ssh"
      user        = "ubuntu"
      private_key = file("../../src/security/instance_key")
      host        = self.public_ip
    }
  }

  # Copy the .env file to the server
  provisioner "file" {
    source = "/home/mrpau/Desktop/Secret_Project/other_layers/Fundy-Main-API/src/.env"
    destination = "/home/ubuntu/Fundy-Main-API/src/.env"

    connection {
      type = "ssh"
      user = "ubuntu"
      private_key = file("../../src/security/instance_key")
      host = self.public_ip
    }
  } 
  
}

# Output the Elastic IP
output "elastic_ip" {
  value       = aws_eip.main_api_eip.public_ip
  description = "The Elastic IP address associated with the EC2 instance."
}