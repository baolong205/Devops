pipeline {
    agent any

    triggers {
        githubPush()
    }

    stages {
        stage('Install dependencies') {
            steps {
                retry(3) {
                    sh '''
                        npm config set fetch-timeout 900000
                        npm config set fetch-retries 5
                        npm config set fetch-retry-mintimeout 20000
                        npm config set fetch-retry-maxtimeout 120000
                        npm ci --prefer-offline --no-audit --no-fund
                    '''
                }
            }
        }

        stage('Prepare assets') {
            steps {
                sh 'npm run prepare-assets'
            }
        }
    }
}