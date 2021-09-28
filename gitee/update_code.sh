#!/usr/bin/env bash

set -x

ROOT_PATH='./Paddle-bot/gitee'

function GithubPaddle_env() {
    repo=$1
    #rm -rf ${ROOT_PATH}/${repo}
    cd ${ROOT_PATH}
    export http_proxy=xxx
    export https_proxy=xxx
    export git=/usr/local/git/bin/git
    /usr/local/git/bin/git clone https://github.com/PaddlePaddle-Gardener/${repo}.git
    ROOT_PATH=$PWD
    echo $ROOT_PATH
    TARGET_PATH=${ROOT_PATH}/${repo}
    BRANCH='develop'
    cd ${TARGET_PATH}
    /usr/local/git/bin/git checkout $BRANCH
    fetch_upstream_develop_if_not_exist 'https://github.com/PaddlePaddle/'${repo}
}

function GiteePaddle_env() {
    repo=$1
    rm -rf ${ROOT_PATH}/gitee_$repo
    cd ${ROOT_PATH}
    http_proxy='' https_proxy='' /usr/local/git/bin/git clone https://gitee.com/paddlepaddle-gardener/$repo.git gitee_$repo
    TARGET_PATH=${ROOT_PATH}/gitee_$repo
    BRANCH='develop'
    cd ${TARGET_PATH}
    /usr/local/git/bin/git checkout $BRANCH
    fetch_upstream_develop_if_not_exist 'https://gitee.com/paddlepaddle/'${repo}
}


function fetch_upstream_develop_if_not_exist() {
    export git=/usr/local/git/bin/git
    UPSTREAM_URL=$1
    origin_upstream_url=`/usr/local/git/bin/git remote -v | awk '{print $1, $2}' | uniq | grep upstream | awk '{print $2}'` 
    if [ "$origin_upstream_url" == "" ]; then
        /usr/local/git/bin/git remote add upstream $UPSTREAM_URL.git
    elif [ "$origin_upstream_url" != "$UPSTREAM_URL" ] \
            && [ "$origin_upstream_url" != "$UPSTREAM_URL.git" ]; then
        /usr/local/git/bin/git remote remove upstream
        /usr/local/git/bin/git remote add upstream $UPSTREAM_URL.git
    fi
    if [ ! -e "$ROOT_PATH/.git/refs/remotes/upstream/$BRANCH" ]; then
        /usr/local/git/bin/git fetch upstream
        /usr/local/git/bin/git pull upstream $BRANCH
    fi
    echo "update Paddle finished as expected" 
}

function prepareCommitEnv() {
    repo=$1
    commitId=$2
    newBranch=$3
    ##github checkout current commitid
    cd ${ROOT_PATH}/$repo
    /usr/local/git/bin/git checkout develop
    /usr/local/git/bin/git checkout $commitId
    ##gitee checkout news bran
    TARGET_PATH=${ROOT_PATH}/gitee_$repo
    cd ${TARGET_PATH}
    /usr/local/git/bin/git checkout -b $newBranch
}

function createPR() {
    export git=/usr/local/git/bin/git
    repo=$1
    newBranch=$2
    commitMessage=$3
    TARGET_PATH=${ROOT_PATH}/gitee_$repo
    cd ${TARGET_PATH}
    /usr/local/git/bin/git add .
    /usr/local/git/bin/git commit -m $commitMessage
    /usr/local/git/bin/git push -f origin $newBranch
    push_res=$?
    while [ $push_res -ne 0 ]
    do
        sleep 10s
        /usr/local/git/bin/git push origin $newBranch
        push_res=$?
    done
    /usr/local/git/bin/git checkout develop
    /usr/local/git/bin/git branch -D $newBranch
}


function main() {
    local CMD=$1
    local repo=$2
    local commitId=$3
    local newbranch=$4
    local title=$5
    case $CMD in
        githubPaddle)
            GithubPaddle_env $repo
            ;;
        giteePaddle)
            GiteePaddle_env $repo
            ;;
        migrateEnv)
            prepareCommitEnv $repo $commitId $newbranch
            ;;
        prepareCode)
            createPR $repo $newbranch $title
            ;;
            *)
            echo "Sorry, $CMD not recognized."
            exit 1
            ;;
        esac
        
}

main $@