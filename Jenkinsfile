pipeline {
    agent any

    triggers {
        githubPush()
    }

    environment {
        VERCEL_ORG_ID = credentials('vercel-org-id')
        VERCEL_PROJECT_ID = credentials('vercel-project-id')
        VERCEL_TOKEN = credentials('vercel-token')
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

        stage('Deploy to Vercel') {
            steps {
                sh '''
                    npx vercel@latest pull --yes --environment=production --token="$VERCEL_TOKEN" --scope="$VERCEL_ORG_ID" --project="$VERCEL_PROJECT_ID"
                    npx vercel@latest build --prod --token="$VERCEL_TOKEN"
                    npx vercel@latest deploy --prebuilt --prod --token="$VERCEL_TOKEN" --scope="$VERCEL_ORG_ID" --project="$VERCEL_PROJECT_ID"
                '''
            }
        }
    }
}