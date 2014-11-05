import base64
import logging

from common.zkOpers import ZkOpers
from tornado.options import options
from common.configFileOpers import ConfigFileOpers
from tornado.httpclient import HTTPClient
from tornado.httpclient import HTTPError
from common.invokeCommand import InvokeCommand

confOpers = ConfigFileOpers()

def issue_mycnf_changed(self):
    keyList = []
    keyList.append('wsrep_cluster_address')
    
    zkOper = ZkOpers('127.0.0.1',2181)
    
    clusterUUID = zkOper.getClusterUUID()
    sourceText,stat = zkOper.retrieveMysqlProp(clusterUUID, issue_mycnf_changed)
    keyValueDict = getDictFromText(sourceText, keyList)
    confOpers.setValue(options.mysql_cnf_file_name, keyValueDict)
    
    
def retrieve_kv_from_db_rows(rows, key_list=None):
    key_value = {}
    
    if rows == None:
        return key_value
    
    if key_list == None:
        return key_value
    
    for i in range(len(rows)):
        key,value = rows[i]
        for j in range(len(key_list)):
            if key_list[j] == key:
                key_value.setdefault(key,value)
    
    return key_value


def _request_fetch(request):
    #access to the target ip machine to retrieve the dict,then modify the config
    http_client = HTTPClient()
    
    response = None
    try:
        response = http_client.fetch(request)
    except HTTPError, e:
        logging.error(e)
    
    return_result = False
    if response != None:    
        if response.error:
            return_result = False
            message = "remote access,the key:%s,error message:%s" % (request,response.error)
            logging.error(message)
        else:
            return_result = response.body.strip()
            
    http_client.close()
            
    return return_result
    
    
def _retrieve_userName_passwd():
    confDict = confOpers.getValue(options.cluster_property, ['adminUser','adminPassword'])
    adminUser = confDict['adminUser']
    adminPasswd = base64.decodestring(confDict['adminPassword'])
    return (adminUser,adminPasswd)

def getDictFromText(sourceText, keyList):
    totalDict = {}
    resultValue = {}
    
    lineList = sourceText.split('\n')
    for line in lineList:
        if not line:
            continue
        
        pos1 = line.find('=')
        key = line[:pos1]
        value = line[pos1+1:len(line)].strip('\n')
        totalDict.setdefault(key,value)
        
    if keyList == None:
        resultValue = totalDict
    else:
        for key in keyList:
            value = totalDict.get(key)
            resultValue.setdefault(key,value)
            
    return resultValue

def check_leader():
    invokeCommand = InvokeCommand()
    ret_str, ret_val = invokeCommand._runSysCmd(options.check_zk_leader)
    if ret_str.find('leader') == -1:
        return False
    return True
