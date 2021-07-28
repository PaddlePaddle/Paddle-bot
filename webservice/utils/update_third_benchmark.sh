#!/usr/bin/env bash

set -x

function GithubPaddle_env() {
    #git clone https://github.com/PaddlePaddle-Gardener/Paddle.git
    ROOT_PATH=$PWD
    TARGET_PATH=${ROOT_PATH}/Paddle
    BRANCH='develop'
    cd ${TARGET_PATH}
    fetch_upstream_develop_if_not_exist
}

function fetch_upstream_develop_if_not_exist() {
    UPSTREAM_URL='https://github.com/PaddlePaddle/Paddle'
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
}

function update_benchmark_thirty_party() {
    #gitclone_env
    #git checkout -b ${up_branch}
    #git submodule init
    #git submodule update --remote
    ROOT_PATH=$PWD
    TARGET_PATH=${ROOT_PATH}/benchmark
    cd ${TARGET_PATH}
    git diff models PaddleSeg PaddleDetection
    git add models PaddleSeg PaddleDetection
    #git diff static_graph/Detection/pytorch/Detectron
    #git add static_graph/Detection/pytorch/Detectron
    git commit -m 'update submodule in benchmark'
    git push origin ${up_branch}
}

function main() {
    local CMD=$1
    local up_branch=$2
    case $CMD in
        githubPaddle)
            GithubPaddle_env
            ;;
            *)
            echo "Sorry, $CMD not recognized."
            exit 1
            ;;
        esac
        echo "update submodule finished as expected" 
}

main $@