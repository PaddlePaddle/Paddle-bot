caught_error

trap 'caught_error' CHLD
EXIT_CODE=0;
function caught_error() {
 for job in `jobs -p`; do
        # echo "PID => ${job}"
        if ! wait ${job} ; then
            echo "At least one test failed with exit code => $?" ;
            EXIT_CODE=1;
        fi
    done
}



#(false|tee tmp; test ${PIPESTATUS[0]} -eq 0)
(false|tee tmp)

echo $?
#wait
