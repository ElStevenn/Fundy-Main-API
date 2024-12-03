pipeline {
    agent any

    stages {
        stage('Build') {
            steps {
                echo 'Build main API Image'
                sudo 'docker build -t main-api .'
            }
        }
        stage('Test') {
            steps {
                echo 'Testing..'
            }
        }
        stage('Deploy') {
            steps {
                echo 'Deploying '
                sudo ' docker run -d -p 8000:8000 --name main-api_v1 --network $network_name main-api'
            }
        }
    }
}