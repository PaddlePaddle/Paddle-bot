#!/usr/bin/env bash

set -x

ROOT_PATH=$PWD

function GithubPaddle_env() {
    cd ${ROOT_PATH}
    flag=1
    while [ $flag != 0 ]
    do
        rm -rf ${ROOT_PATH}/Paddle
        git clone https://github.com/PaddlePaddle-Gardener/Paddle.git
        flag=$?
        sleep 10
    done
    ROOT_PATH=$PWD
    echo $ROOT_PATH
    TARGET_PATH=${ROOT_PATH}/Paddle
    BRANCH='develop'
    cd ${TARGET_PATH}
    git checkout $BRANCH
    fetch_upstream_develop_if_not_exist 'https://github.com/PaddlePaddle/Paddle'
}

function GiteePaddle_env() {
    cd ${ROOT_PATH}
    flag=1
    while [ $flag != 0 ]
    do
        rm -rf ${ROOT_PATH}/gitee_Paddle
        git clone https://gitee.com/paddlepaddle-gardener/Paddle.git gitee_Paddle
        flag=$?
        sleep 10
    done
    TARGET_PATH=${ROOT_PATH}/gitee_Paddle
    BRANCH='develop'
    cd ${TARGET_PATH}
    /usr/local/git/bin/git checkout $BRANCH
    fetch_upstream_develop_if_not_exist 'https://gitee.com/paddlepaddle/Paddle'
}

function GiteePaddle_env_update() {
    echo '********************cesar************************'
    TARGET_PATH=${ROOT_PATH}/gitee_Paddle
    BRANCH='develop'
    cd ${TARGET_PATH}
    git checkout ${BRANCH}
    git fetch upstream
    git pull upstream $BRANCH
    # fetch_upstream_develop_if_not_exist 'https://gitee.com/paddlepaddle/Paddle'
    echo '********************cesar************************'
}

function fetch_upstream_develop_if_not_exist() {
    UPSTREAM_URL=$1
    echo $UPSTREAM_URL
    origin_upstream_url=`git remote -v | awk '{print $1, $2}' | uniq | grep upstream | awk '{print $2}'` 
    if [ "$origin_upstream_url" == "" ]; then
        git remote add upstream $UPSTREAM_URL.git
    elif [ "$origin_upstream_url" != "$UPSTREAM_URL" ] \
            && [ "$origin_upstream_url" != "$UPSTREAM_URL.git" ]; then
        git remote remove upstream
        git remote add upstream $UPSTREAM_URL.git
    fi
    if [ ! -e "$ROOT_PATH/.git/refs/remotes/upstream/$BRANCH" ]; then
        git fetch upstream
        git pull upstream $BRANCH
    fi
    echo "update Paddle finished as expected" 
}

function prepareCommitEnv() {
    commitId=$1
    newBranch=$2
    ##github checkout current commitid
    cd ${ROOT_PATH}/Paddle
    git checkout develop
    git checkout $commitId
    ##gitee checkout news bran
    TARGET_PATH=${ROOT_PATH}/gitee_Paddle
    cd ${TARGET_PATH}
    git checkout -b $newBranch
}

function createPR() {
    TARGET_PATH=${ROOT_PATH}/gitee_Paddle
    newBranch=$1
    commitMessage=$2
    cd ${TARGET_PATH}
    git add .
    git commit -m $commitMessage
    git push -f origin $newBranch
    push_res=$?
    while [ $push_res -ne 0 ]
    do
        sleep 10s
        git push origin $newBranch
        push_res=$?
    done
    git checkout develop
    git branch -D $newBranch
}



function main() {
    local CMD=$1
    local commitId=$2
    local newbranch=$3
    local title=$4
    # TODO: delete http_proxy
    echo ${USER}
    echo ${HOME}
    PATH=${PATH}:/usr/local/git/bin/
    export http_proxy=http://172.19.57.45:3128
    export https_proxy=http://172.19.57.45:3128
    case $CMD in
        githubPaddle)
            GithubPaddle_env
            ;;
        giteePaddle)
            GiteePaddle_env
            ;;
        migrateEnv)
            prepareCommitEnv $commitId $newbranch
            ;;
        prepareCode)
            createPR $newbranch $title
            ;;
        giteePaddle_env_update)
            GiteePaddle_env_update
            ;;
            *)
            echo "Sorry, $CMD not recognized."
            exit 1
            ;;
        esac
        
}

main $@
