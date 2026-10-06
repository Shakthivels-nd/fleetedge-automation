// FleetEdge automation 
//
// Prerequisites on Jenkins:
//   * No .env needed: device id/ip, OTA version and environment come from the build parameters.
//   * An agent labelled "deviceqa-laptop-2" with python3 + venv that can reach the device.
pipeline {
    agent { label params.AGENT_LABEL ?: 'deviceqa-laptop-2' }

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '30'))
        disableConcurrentBuilds()   // one device == one run at a time
    }

    parameters {
        string(name: 'AGENT_LABEL', defaultValue: 'deviceqa-laptop-2', description: 'Jenkins agent label (must have network access to the device)')
        string(name: 'BRANCH', defaultValue: 'main', description: 'Git branch to test')
        string(name: 'SERVICES', defaultValue: '', description: 'Comma separated services to test, e.g. "scheduler,awsiot" (folder names under src/tests, or "sanity" for the sanity file). Blank = all')
        string(name: 'DEVICE_ID', defaultValue: '', description: 'Device ID under test (required)')
        string(name: 'DEVICE_IP', defaultValue: '', description: 'Device IP under test (required)')
        string(name: 'OTA_VERSION', defaultValue: '', description: 'OTA version being tested (required)')
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
                script { currentBuild.description = "${params.BRANCH} | ${params.SERVICES ?: 'all'} | ${params.DEVICE_IP ?: 'n/a'}" }
            }
        }

        stage('Setup') {
            steps {
                sh '''
                    set -e
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install -q --upgrade pip
                    pip install -q -r requirements.txt
                '''
            }
        }

        stage('Trust device SSH key') {
            when { expression { params.DEVICE_IP?.trim() } }
            steps {
                // The tests ssh to the pod non-interactively (sshpass), so the agent user must already
                // know the pod's host key. Add it once; keeps host-key checking on.
                withEnv(["P_IP=${params.DEVICE_IP.trim()}"]) {
                    sh '''
                        mkdir -p ~/.ssh && chmod 700 ~/.ssh
                        touch ~/.ssh/known_hosts && chmod 600 ~/.ssh/known_hosts
                        if ! ssh-keygen -F "$P_IP" >/dev/null 2>&1; then
                            ssh-keyscan -T 10 -H "$P_IP" >> ~/.ssh/known_hosts
                        fi
                    '''
                }
            }
        }

        stage('Run tests') {
            steps { script {
                // Parameters go through env vars (not Groovy interpolation) to avoid shell injection.
                withEnv([
                    "P_SERVICES=${params.SERVICES}",
                    "P_ID=${params.DEVICE_ID}",
                    "P_IP=${params.DEVICE_IP}",
                    "P_OTA=${params.OTA_VERSION}",
                    "P_ENV=${params.ENVIRONMENT}",
                    "P_SKIP=${params.SKIP_REBOOT}",
                ]) {
                    def rc = sh(returnStatus: true, script: '''
                        . .venv/bin/activate
                        [ -n "$P_ID" ]  && export DEVICE_ID="$P_ID"
                        [ -n "$P_IP" ]  && export DEVICE_IP="$P_IP"
                        [ -n "$P_OTA" ] && export OTA_VERSION="$P_OTA"
                        export ENVIRONMENT="$P_ENV"
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
                            if [ "${svc,,}" = "sanity" ]; then paths+=(src/tests/test_sanity_functions.py); continue; fi
                            dir=$(find src/tests -maxdepth 1 -mindepth 1 -type d -iname "$svc" | head -n1)
                            [ -z "$dir" ] && { echo "Unknown service '$svc'. Available:"; ls -d src/tests/*/ | xargs -n1 basename; exit 2; }
                            paths+=("$dir")
                        done
                        [ ${#paths[@]} -eq 0 ] && paths=(src/tests)
                        python -m pytest "${paths[@]}" "${args[@]}" 2>&1 | tee pytest.log
                        exit ${PIPESTATUS[0]}
                    ''')
                    // Red (FAILURE) only when no test actually ran (setup/connection errors, bad service
                    // name, crash, nothing collected). If at least one test passed or failed, the suite ran:
                    // all passed -> SUCCESS, some failed -> UNSTABLE (yellow), details in Test_report.
                    def testsRan = sh(returnStatus: true,
                        script: "tail -n 1 pytest.log | grep -Eq '[0-9]+ (passed|failed)'") == 0
                    if (rc == 0) {
                        // all passed
                    } else if (testsRan) {
                        unstable('Some tests failed - see Test_report')
                    } else {
                        error("No tests ran (pytest exit code ${rc}) - check the console log")
                    }
                }
            } }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'pytest.log, src/reports/**', allowEmptyArchive: true
            publishHTML(target: [
                reportDir: 'src/reports', reportFiles: 'live_report.html',
                reportName: 'Test_report', keepAll: true, allowMissing: true, alwaysLinkToLastBuild: true
            ])
        }
    }
}
