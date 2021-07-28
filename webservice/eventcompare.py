@router.register("pull_request", action="opened")
async def pull_request_event_template(event, gh, repo, *args, **kwargs):
    pr_num = event.data['number']
    url = event.data["pull_request"]["comments_url"]
    BODY = event.data["pull_request"]["body"]
    sha = event.data["pull_request"]["head"]["sha"]
    await create_check_run(sha, gh, repo)
    if repo not in ['PaddlePaddle/Paddle', 'PaddlePaddle/benchmark', 'lelelelelez/leetcode', 'PaddlePaddle/FluidDoc']:
        repo = 'Others'
    CHECK_TEMPLATE = localConfig.cf.get(repo, 'CHECK_TEMPLATE')
    global check_pr_template
    global check_pr_template_message
    check_pr_template, check_pr_template_message = checkPRTemplate(repo, BODY, CHECK_TEMPLATE)
    logger.info("check_pr_template: %s pr: %s" %(check_pr_template, pr_num))
    if check_pr_template == False:
        message = localConfig.cf.get(repo, 'NOT_USING_TEMPLATE')
        logger.error("%s Not Follow Template." % pr_num)
        if event.data['action'] == "opened":
            await gh.post(url, data={"body": message})
    else:
        comment_list = checkComments(url)
        for i in range(len(comment_list)):
            comment_sender = comment_list[i]['user']['login']
            comment_body = comment_list[i]['body']
            if comment_sender in ["paddle-bot[bot]", "just-test-paddle[bot]"] and comment_body.startswith('❌'):
                message = localConfig.cf.get(repo, 'PR_CORRECT_DESCRIPTION')
                logger.info("%s Correct PR Description and Meet Template" %pr_num)
                update_url = comment_list[i]['url']
                await gh.patch(update_url, data={"body": message})