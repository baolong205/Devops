pipeline {
    agent { label 'clinic-ci-linux' }
    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        timeout(time: 60, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '10'))
    }
    parameters {
        string(name: 'SOURCE_REF', defaultValue: 'codex/milestone-4', description: 'Branch/ref of vxxngw/DevOps; never a repository URL')
        string(name: 'SOURCE_BRANCH', defaultValue: 'codex/milestone-4', description: 'Webhook branch for provenance; deployment additionally checks origin/main')
        string(name: 'CLUSTER_SERVER_URL', defaultValue: 'https://192.168.150.11:6443', description: 'Must match the actual dedicated Terraform k3s server and trusted kubeconfig')
        string(name: 'STAGING_URL', defaultValue: 'https://staging.anuyen.test', description: 'Trusted HTTPS URL with DNS/hosts configured')
        string(name: 'PRODUCTION_URL', defaultValue: 'https://hospital.anuyen.test', description: 'Trusted HTTPS URL with DNS/hosts configured')
        booleanParam(name: 'IS_PR', defaultValue: false, description: 'PR verification: no registry or deployment credentials')
        booleanParam(name: 'PUBLISH_IMAGES', defaultValue: false, description: 'Publish a SHA-tagged candidate after every gate passes; disabled for PRs')
        booleanParam(name: 'DEPLOY', defaultValue: false, description: 'Mốc3: requires Kubernetes overlays, namespace credentials and smoke accounts')
        choice(name: 'SECURITY_DEMO', choices: ['none', 'secret', 'critical'], description: 'Intentional negative gate; must fail before push/deploy')
        string(name: 'PRODUCTION_APPROVERS', defaultValue: 'clinic-admin', description: 'Real Jenkins users permitted to approve production')
        string(name: 'REGISTRY_NAMESPACE', defaultValue: 'ghcr.io/vxxngw', description: 'GHCR namespace owned by the registry credential account')
    }
    environment {
        CLINIC_REGISTRY = "${params.REGISTRY_NAMESPACE}"
        TRIVY_CACHE_DIR = '/home/jenkins/.cache/trivy'
        PIP_INDEX_URL = 'https://pypi.org/simple'
        PIP_DISABLE_PIP_VERSION_CHECK = '1'
    }
    stages {
        stage('Checkout') {
            steps {
                script {
                    if (!(params.REGISTRY_NAMESPACE ==~ /ghcr\.io\/[a-z0-9][a-z0-9-]{0,38}/)) {
                        error('Invalid GHCR namespace')
                    }
                    if (!(params.SOURCE_REF ==~ /[a-zA-Z0-9][a-zA-Z0-9._\/-]{0,160}/)) {
                        error('Invalid SOURCE_REF')
                    }
                    if (params.IS_PR && (params.PUBLISH_IMAGES || params.DEPLOY)) {
                        error('PR verification cannot publish or deploy')
                    }
                    deleteDir()
                    checkout scm
                    env.CLINIC_COMMIT = sh(script: 'git rev-parse HEAD', returnStdout: true).trim()
                    if (params.SOURCE_REF ==~ /[a-f0-9]{40}/ && env.CLINIC_COMMIT != params.SOURCE_REF) {
                        error('Checkout is not the exact webhook commit')
                    }
                    env.CLINIC_IS_PR = params.IS_PR.toString()
                    if (params.DEPLOY) {
                        def mainCommit = sh(script: 'git rev-parse refs/remotes/origin/main', returnStdout: true).trim()
                        if (env.CLINIC_COMMIT != mainCommit) { error('Deployment is restricted to the current main commit; review is a separate Git policy') }
                    }
                }
            }
        }
        stage('Secret scan') {
            steps { sh 'python3 -m ci.security secrets' }
        }
        stage('Security failure demonstration') {
            when { expression { params.SECURITY_DEMO != 'none' } }
            steps {
                script {
                    if (params.SECURITY_DEMO == 'secret') {
                        sh 'python3 -m ci.security demo-secret'
                    } else {
                        sh 'python3 -m ci.security demo-critical'
                    }
                    error('Negative security demonstration unexpectedly passed')
                }
            }
        }
        stage('Lint and typecheck') {
            steps { sh 'python3 -m ci.pipeline prepare && python3 -m ci.pipeline lint' }
        }
        stage('Unit tests') {
            steps { sh 'python3 -m ci.pipeline unit' }
        }
        stage('Infrastructure configuration checks') {
            steps { sh 'python3 -m ci.pipeline infrastructure' }
        }
        stage('Observability configuration checks') {
            steps { sh 'python3 -m ci.pipeline observability' }
        }
        stage('Build images') {
            steps { sh 'python3 -m ci.pipeline build' }
        }
        stage('Integration tests') {
            steps { sh 'python3 -m ci.pipeline integration' }
        }
        stage('Image and dependency security scan') {
            steps { sh 'python3 -m ci.security images' }
        }
        stage('Push SHA images and record digests') {
            when { expression { params.PUBLISH_IMAGES && !params.IS_PR } }
            steps {
                withCredentials([usernamePassword(credentialsId: 'clinic-ghcr', usernameVariable: 'CLINIC_REGISTRY_USER', passwordVariable: 'CLINIC_REGISTRY_TOKEN')]) {
                    sh 'python3 -m ci.release publish'
                }
            }
        }
        stage('Deploy staging') {
            when { expression { params.DEPLOY && !params.IS_PR } }
            steps {
                script {
                    if (!params.PUBLISH_IMAGES) { error('Deployment requires a published, scanned release') }
                }
                withCredentials([file(credentialsId: 'clinic-kubeconfig-staging', variable: 'KUBECONFIG'), file(credentialsId: 'clinic-lab-ca', variable: 'CLINIC_SMOKE_CA_FILE'), usernamePassword(credentialsId: 'clinic-smoke-staging', usernameVariable: 'CLINIC_SMOKE_EMAIL', passwordVariable: 'CLINIC_SMOKE_PASSWORD')]) {
                    withEnv(["CLINIC_EXPECTED_CLUSTER_SERVER=${params.CLUSTER_SERVER_URL}", "CLINIC_SMOKE_URL=${params.STAGING_URL}"]) {
                        sh 'python3 -m ci.pipeline deploy-staging'
                    }
                }
                archiveArtifacts artifacts: 'ci-out/staging-deploy-result.json,ci-out/staging-release.json,ci-out/release-manifest.json', fingerprint: true
            }
        }
        stage('Approve production') {
            when { expression { params.DEPLOY && !params.IS_PR } }
            steps {
                timeout(time: 15, unit: 'MINUTES') {
                    input message: "Promote the same scanned digests? Staging: ${params.STAGING_URL} | Evidence: ${env.BUILD_URL}artifact/ci-out/staging-deploy-result.json | Manifest: ${env.BUILD_URL}artifact/ci-out/release-manifest.json", ok: 'Promote', submitter: params.PRODUCTION_APPROVERS
                }
            }
        }
        stage('Deploy production') {
            when { expression { params.DEPLOY && !params.IS_PR } }
            steps {
                withCredentials([file(credentialsId: 'clinic-kubeconfig-production', variable: 'KUBECONFIG'), file(credentialsId: 'clinic-lab-ca', variable: 'CLINIC_SMOKE_CA_FILE'), usernamePassword(credentialsId: 'clinic-smoke-production', usernameVariable: 'CLINIC_SMOKE_EMAIL', passwordVariable: 'CLINIC_SMOKE_PASSWORD')]) {
                    withEnv(["CLINIC_EXPECTED_CLUSTER_SERVER=${params.CLUSTER_SERVER_URL}", "CLINIC_SMOKE_URL=${params.PRODUCTION_URL}"]) {
                        sh 'python3 -m ci.pipeline deploy-production'
                    }
                }
            }
        }
    }
    post {
        always {
            junit testResults: 'ci-out/junit-*.xml', allowEmptyResults: true
            archiveArtifacts artifacts: 'ci-out/**', allowEmptyArchive: true
            sh returnStatus: true, script: 'python3 -m ci.release cleanup'
        }
    }
}
