pipeline {
    agent any

    triggers {
        githubPush()
    }

    stages {
        stage('Install dependencies') {
            steps {
                sh 'npm ci'
            }
        }

        stage('Prepare assets') {
            steps {
                sh 'npm run prepare-assets'
            }
        }
    }
}