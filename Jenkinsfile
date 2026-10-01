// FleetEdge automation -- parameterised pytest run, triggerable remotely:
//   curl -u USER:API_TOKEN -X POST "http://10.200.8.71:8080/job/<JOB>/buildWithParameters" \
//        --data-urlencode SERVICES="scheduler,btfv" \
//        --data-urlencode DEVICE_IP=10.x.x.x --data-urlencode SKIP_REBOOT=true
//
// Prerequisites on Jenkins:
//   * Secret-file credential "fe-env-file" holding the contents of .env
//     (DB_*, IDMS_*, HOST*, JIRA_* ...). DEVICE_ID/DEVICE_IP/etc. below override it.
//   * An agent labelled "deviceqa-laptop-2" with python3 + venv that can reach the device.
pipeline {
    agent { label params.AGENT_LABEL ?: 'deviceqa-laptop-2' }

    options {
        timestamps()
        timeout(time: 8, unit: 'HOURS')
        buildDiscarder(logRotator(numToKeepStr: '30'))
        disableConcurrentBuilds()   // one device == one run at a time
    }

    parameters {
        string(name: 'AGENT_LABEL', defaultValue: 'deviceqa-laptop-2', description: 'Jenkins agent label (must have network access to the device)')
        string(name: 'BRANCH', defaultValue: 'main', description: 'Git branch to test')
        string(name: 'SERVICES', defaultValue: '', description: 'Comma separated services to test, e.g. "scheduler,awsiot" (folder names under src/tests). Blank = all services')
        string(name: 'DEVICE_ID', defaultValue: '', description: 'Device ID under test (blank = value from .env)')
        string(name: 'DEVICE_IP', defaultValue: '', description: 'Device IP under test (blank = value from .env)')
        string(name: 'OTA_VERSION', defaultValue: '', description: 'OTA version being tested (blank = value from .env)')
        choice(name: 'ENVIRONMENT', choices: ['Staging', 'Prod'], description: 'Target environment')
        booleanParam(name: 'SKIP_REBOOT', defaultValue: false, description: 'Pass --skip-reboot (skips ~10 min voyager reboot + DRIVE mode setup)')
    }

    environment {
        PYTHONUNBUFFERED = '1'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout([$class: 'GitSCM',
                          branches: [[name: "*/${params.BRANCH}"]],
                          userRemoteConfigs: scm.userRemoteConfigs])
                script { currentBuild.description = "${params.BRANCH} | ${params.SERVICES ?: 'all'} | ${params.DEVICE_IP ?: 'env-ip'}" }
            }
        }

        stage('Setup') {
            steps {
                withCredentials([file(credentialsId: 'fe-env-file', variable: 'FE_ENV_FILE')]) {
                    sh '''
                        set -e
                        cp "$FE_ENV_FILE" .env
                        chmod 600 .env
                        python3 -m venv .venv
                        . .venv/bin/activate
                        pip install -q --upgrade pip
                        pip install -q -r requirements.txt
                    '''
                }
            }
        }

        stage('Run tests') {
            steps {
                // Parameters go through env vars (not Groovy interpolation) to avoid shell injection.
                withEnv([
                    "P_SERVICES=${params.SERVICES}",
                    "P_ID=${params.DEVICE_ID}",
                    "P_IP=${params.DEVICE_IP}",
                    "P_OTA=${params.OTA_VERSION}",
                    "P_ENV=${params.ENVIRONMENT}",
                    "P_SKIP=${params.SKIP_REBOOT}",
                ]) {
                    sh '''
                        . .venv/bin/activate
                        args=()
                        [ -n "$P_ID" ]   && args+=(--device-id "$P_ID")
                        [ -n "$P_IP" ]   && args+=(--device-ip "$P_IP")
                        [ -n "$P_OTA" ]  && args+=(--ota-version "$P_OTA")
                        args+=(--env "$P_ENV")
                        [ "$P_SKIP" = "true" ] && args+=(--skip-reboot)
                        # "scheduler, AWSIoT" -> src/tests/scheduler src/tests/awsiot (case-insensitive folder match)
                        paths=()
                        IFS=',' read -ra svcs <<< "$P_SERVICES"
                        for svc in "${svcs[@]}"; do
                            svc=$(echo "$svc" | xargs)
                            [ -z "$svc" ] && continue
                            dir=$(find src/tests -maxdepth 1 -mindepth 1 -type d -iname "$svc" | head -n1)
                            [ -z "$dir" ] && { echo "Unknown service '$svc'. Available:"; ls -d src/tests/*/ | xargs -n1 basename; exit 2; }
                            paths+=("$dir")
                        done
                        [ ${#paths[@]} -eq 0 ] && paths=(src/tests)
                        # Keep the stage red on test failures but still publish reports.
                        python -m pytest "${paths[@]}" "${args[@]}" 2>&1 | tee pytest.log
                        exit ${PIPESTATUS[0]}
                    '''
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'pytest.log, src/reports/**', allowEmptyArchive: true
            publishHTML(target: [
                reportDir: 'src/reports', reportFiles: 'live_report.html',
                reportName: 'Test_report', keepAll: true, allowMissing: true, alwaysLinkToLastBuild: true
            ])
            sh 'rm -f .env'
        }
    }
}
