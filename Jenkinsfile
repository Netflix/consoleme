@Library('factual-shared-libs') _
pipeline {
    agent none
    stages {
        stage ('Build') {
            steps {
                docker_build name: 'infraeng-consoleme'
            }
        }
    }
}