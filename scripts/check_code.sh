#!/usr/bin/env bash

# Copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#=================================================
#                   Utils
#=================================================

set -ex

if [ -z ${BRANCH} ]; then
    BRANCH="master"
fi

PADDLEBOT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}")/.." && pwd )"
echo ${PADDLEBOT_ROOT}

function prepare_env(){
    pip install pre-commit==1.21 pylint==1.9.5 -i https://pypi.tuna.tsinghua.edu.cn/simple
}

function abort(){
    echo "Your change doesn't follow python's code style." 1>&2
    echo "Please use pre-commit to check what is wrong." 1>&2
    exit 1
}


function check_style(){
	trap 'abort' 0
	pre-commit install
	commit_files=on
	for file_name in `git diff --name-only HEAD~ HEAD`;do
	        if  ! pre-commit run --files $file_name ; then
            		git diff
            		commit_files=off
        	fi
    	done
    	if [ $commit_files == 'off' ];then
        	echo "code format error"
        	exit 1
    	fi
    	trap 0
}

function main(){
    local CMD=$1
    case $CMD in
      check_code_style)
        prepare_env
        check_style
        ;;
	*)
        echo "Sorry, $CMD not recognized."
        exit 1
        ;;
      esac
      echo "runtest script finished as expected"
}

main $@
