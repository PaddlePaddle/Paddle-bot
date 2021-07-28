import sys
sys.path.append("..")
from utils.handler import xlyHandler

class Resource(xlyHandler):
    def getEachResource(self):
        """
        this function will get resource actual count by cardType.
        Returns:
            resource_dict: {agentname: executorCount}
        """
        labels = self.getAllResource().json()['entities']['labels']
        resource_dict = {}
        for label in labels:
            agent_name = label['displayName']
            agent_details = self.getConcurrenceByResourceId(label['id']).json()
            executorCount = self.getAgentExecutorCount(agent_details)
            resource_dict[agent_name] = executorCount
        print(resource_dict)
        return resource_dict

    def getAgentExecutorCount(self, res):
        """
        this function will get agent executorCount .
        Returns:
            executorCount: int
        """
        agents = res['entities']['agents']
        executorCount = 0
        for agent in agents:
            if agent['status'] == 'ONLINE':
                executorCount += agent['executorCount']
        return executorCount

#Resource().getEachResource()
