from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from utils.readConfig import ReadConfig
import logging
from regularClose_auth import regularClose_job
import sys 
sys.path.append("..")
from gitee.pr_merge import gitee_merge_pr
from gitee.pr_migration import githubPrMigrateGitee
import time

localConfig = ReadConfig(path='conf/job.conf')

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename='logs/weekly_sched.log',
                    filemode='a')

def job_listener(event):
    """set a job listener"""
    logging.info('listenning on...%s' % str(event))
    if event.exception:
        print(event.exception)
        logging.info('exception happend')
    else:
        logging.info('job passed')


def daily_jobs():
    """seched of weekly jobs"""
    executors = {'default': ThreadPoolExecutor(max_workers=30), \
                 'processpool': ProcessPoolExecutor(max_workers=30)}
    sched = BackgroundScheduler(executors=executors)
    cf = localConfig.cf
    job = 'regularClose_job'
    sched.add_job(regularClose_job, cf.get(job, 'type'), day_of_week=cf.get(job, 'day_of_week'), hour=cf.get(job, 'hour'), minute=cf.get(job, 'minute'), \
                    second=cf.get(job, 'second'), misfire_grace_time=int(cf.get(job, 'misfire_grace_time')))
    job = 'giteeMergePR_job'
    sched.add_job(gitee_merge_pr, cf.get(job, 'type'), day_of_week=cf.get(job, 'day_of_week'), hour=cf.get(job, 'hour'), minute=cf.get(job, 'minute'), \
                    second=cf.get(job, 'second'), misfire_grace_time=int(cf.get(job, 'misfire_grace_time')))
    job = 'giteeMigratePR_job'
    sched.add_job(githubPrMigrateGitee().main, cf.get(job, 'type'), day_of_week=cf.get(job, 'day_of_week'), hour=cf.get(job, 'hour'), minute=cf.get(job, 'minute'), \
                    second=cf.get(job, 'second'), misfire_grace_time=int(cf.get(job, 'misfire_grace_time')))

    sched.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    sched._logger = logging
    sched.start()
    while True:
        time.sleep(3)

if __name__ == "__main__":
    daily_jobs()