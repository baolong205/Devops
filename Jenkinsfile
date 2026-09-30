def sendTelegram(String message) {
    withEnv(["TELEGRAM_MESSAGE=${message}"]) {
        try {
            sh '''
                node -e 'const url = "https://api.telegram.org/bot" + process.env.TELEGRAM_BOT_TOKEN + "/sendMessage"; fetch(url, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ chat_id: process.env.TELEGRAM_CHAT_ID, text: process.env.TELEGRAM_MESSAGE }) }).then(async response => { const result = await response.json(); if (!response.ok || !result.ok) throw new Error(result.description || "Telegram HTTP " + response.status); }).catch(error => { console.error(error.message); process.exitCode = 1; });'
            '''
        } catch (err) {
            echo 'Telegram notification failed; continuing the Jenkins pipeline.'
        }
    }
}

pipeline {
    agent any

    triggers {
        githubPush()
    }

    environment {
        VERCEL_ORG_ID = credentials('vercel-org-id')
        VERCEL_PROJECT_ID = credentials('vercel-project-id')
        VERCEL_TOKEN = credentials('vercel-token')
        TELEGRAM_BOT_TOKEN = credentials('telegram-bot-token')
        TELEGRAM_CHAT_ID = credentials('telegram-chat-id')
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
                script {
                    def branch = env.BRANCH_NAME ?: (env.GIT_BRANCH ?: 'main').replaceFirst('^origin/', '')
                    def commit = env.GIT_COMMIT ?: sh(script: 'git rev-parse HEAD', returnStdout: true).trim()
                    sendTelegram("🚀 Bắt đầu deploy website\nRepository: https://github.com/baolong205/Devops\nBranch: ${branch}\nCommit: ${commit}")
                }
                sh '''
                    npx vercel@latest pull --yes --environment=production --token="$VERCEL_TOKEN" --scope="$VERCEL_ORG_ID" --project="$VERCEL_PROJECT_ID"
                    npx vercel@latest build --prod --token="$VERCEL_TOKEN"
                    npx vercel@latest deploy --prebuilt --prod --token="$VERCEL_TOKEN" --scope="$VERCEL_ORG_ID" --project="$VERCEL_PROJECT_ID"
                '''
            }
        }
    }

    post {
        success {
            script {
                def branch = env.BRANCH_NAME ?: (env.GIT_BRANCH ?: 'main').replaceFirst('^origin/', '')
                sendTelegram("✅ Deploy thành công\nRepository: https://github.com/baolong205/Devops\nBranch: ${branch}\nWebsite: https://project-spring-boot-wugh.vercel.app")
            }
        }
        failure {
            script {
                def branch = env.BRANCH_NAME ?: (env.GIT_BRANCH ?: 'main').replaceFirst('^origin/', '')
                def commit = env.GIT_COMMIT ?: 'unknown'
                sendTelegram("❌ Deploy thất bại\nRepository: https://github.com/baolong205/Devops\nBranch: ${branch}\nCommit: ${commit}\nError: Pipeline thất bại; xem Console Output của build #${env.BUILD_NUMBER}")
            }
        }
    }
}