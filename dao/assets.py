#!/usr/bin/env python  
# _#_ coding:utf-8 _*_ 
import uuid,xlrd, json
from asset.models import *
from deploy.models import *
from databases.models import *
from navbar.models import *
from sched.models import *
from wiki.models import *
from orders.models import *
from django.contrib.auth.models import Group
from account.models import User,Structure
from utils.logger import logger
from dao.base import DataHandle
from django.http import QueryDict
from libs.ansible.runner import ANSRunner
from cicd.models import Project_Config
from django.db.models import Q

class AssetsBusiness(object):
    def __init__(self):
        super(AssetsBusiness, self).__init__()  
        
    def get_node_json_assets(self,business):
        dataList = []
        for ds in business.assets_set.all():
            dataList.append(ds.to_json())
        return dataList
    
    def get_node_json_project(self,business):
        dataList = []
        for ds in Project_Config.objects.filter(project_business=business.id):
            dataList.append(ds.to_base_json())
        return dataList    
    
    def get_assets(self,business):
        return business.assets_set.all()
    
    def get_nodes_all_children(self,tree_id,lft,rght):
        return Business_Tree_Assets.objects.filter(tree_id=tree_id,lft__gt=lft,rght__lt=rght)
    
    def get_node_unallocated_json_assets(self,business):
        dataList = []
        for ds in Assets.objects.filter(~Q(business_tree=business)):
            dataList.append(ds.to_json())  
        return dataList      

    def get_node_unallocated_assets(self,business):
        return Assets.objects.filter(~Q(business_tree=business)) 
    
class AssetsBase(DataHandle):
    def __init__(self):
        super(AssetsBase, self).__init__()
        self.uuid = uuid.uuid4()
        self.name = uuid.uuid4().hex[0:8].upper() 
        
    def userList(self):   
        return User.objects.all()
    
    def serviceList(self):
        return Service_Assets.objects.all()

    def cabinetList(self):
        return Cabinet_Assets.objects.all()  
    
    def tagsList(self):
        return Tags_Assets.objects.all()      
    
    def zoneList(self):
        return Zone_Assets.objects.all()
        
    def idcList(self):
        return Idc_Assets.objects.all()
    
    def raidList(self):
        return Raid_Assets.objects.all()    
    
    def lineList(self):
        return Line_Assets.objects.all()     
    
    def assetsList(self):
        return Assets.objects.all()
    
    def groupList(self):
        dicts = []
        for ds in Structure.objects.filter(level__gt=0):
            if ds.last_node() > 0:dicts.append(ds.to_json())
        return dicts
    
    def manufacturerList(self):
        try:
            return [ ds.manufacturer  for ds in Assets.objects.raw("""SELECT manufacturer,id from opsmanage_assets WHERE  manufacturer is not null GROUP BY manufacturer""")]
        except Exception as ex:
            logger.error(msg="获取设备厂商失败:{ex}".format(ex=ex))
        return []        

    def providerList(self):
        try:
            return [ ds.provider  for ds in Assets.objects.raw("""SELECT provider,id from opsmanage_assets WHERE  provider is not null GROUP BY provider""")] 
        except Exception as ex:
            logger.error(msg="获取供应商失败:{ex}".format(ex=ex))
        return []  

    def modelList(self):
        try:
            return [ ds.model  for ds in Assets.objects.raw("""SELECT model,id from opsmanage_assets WHERE  model is not null GROUP BY model""")]
        except Exception as ex:
            logger.error(msg="获取设备型号失败:{ex}".format(ex=ex))
        return [] 
    
    def cpuList(self):
        try:
            return [ ds.cpu  for ds in Server_Assets.objects.raw("""SELECT cpu,id from opsmanage_server_assets WHERE  cpu is not null GROUP BY cpu""")]
        except Exception as ex:
            logger.error(msg="获取cpu型号失败:{ex}".format(ex=ex))
        return [] 
               
    def systemList(self):
        try:
            return [ ds.system  for ds in Server_Assets.objects.raw("""SELECT system,id from opsmanage_server_assets WHERE  system is not null GROUP BY system""")]
        except Exception as ex:
            logger.error(msg="获取操作系统失败:{ex}".format(ex=ex))
        return [] 
    
    def kernelList(self):
        try:
            return [ ds.kernel  for ds in Server_Assets.objects.raw("""SELECT kernel,id from opsmanage_server_assets WHERE  kernel is not null GROUP BY kernel""")]
        except Exception as ex:
            logger.error(msg="获取内核版本失败:{ex}".format(ex=ex))
        return []     
      
    
    def base(self):
        return {"userList":self.userList(),"idcList":self.idcList(),               
                "name":self.name,"serverList":self.serverList(),
                "inventoryList":self.inventoryList(),"uuid": uuid.uuid4(),
                "cabinetList":self.cabinetList(),"lineList":self.lineList(),
                "manufacturerList":self.manufacturerList(),"modelList":self.modelList(),
                "providerList":self.providerList(),"cpuList":self.cpuList(),
                "systemList":self.systemList(),"kernelList":self.kernelList(),
                "tagsList":self.tagsList(),"zoneList":self.zoneList(),
                "raidList":self.raidList(),"groupList":self.groupList(),
                }  
        
    def assets(self,id):
        try:
            return  Assets.objects.get(id=id) 
        except Exception as ex:
            logger.error(msg="获取资产失败:{ex}".format(ex=ex))       
            return False
    
    def inventoryList(self):
        return Deploy_Inventory.objects.all()

    def allowcator(self,sub,args,request=None):
        if hasattr(self,sub):
            func= getattr(self,sub)
            return func(args,request)
        else:
            logger.error(msg="AssetsBase没有{sub}方法".format(sub=sub))       
            return []         
                                                              
    
    def check_user_assets(self,userid,assetsid):
        try:
            user = User.objects.get(id=userid)
        except Exception as ex:
            logger.warn(msg="查询用户信息失败: {ex}".format(ex=str(ex)))  
            return False
        try:
            assets = Assets.objects.get(id=assetsid)
        except Exception as ex:
            logger.warn(msg="查询资产信息失败: {ex}".format(ex=str(ex)))  
            return False  
        
        if user.is_superuser and assets:
            return assets
        
        if not user.is_superuser and assets \
            and user.has_perm('asset.assets_webssh_server'): 
            try:     
                if User_Server.objects.get(user=user,assets=assets):return assets
            except Exception as ex:
                logger.warn(msg="查询用户资产信息失败: {ex}".format(ex=str(ex)))  
                return False        
        return False
    
    def query_user_assets(self,request,assetsList):
        if request.user.is_superuser:
            return  assetsList   
        assets_list =[ das.assets for das in User_Server.objects.filter(user=request.user,assets__in=assetsList)]       
        return assets_list
    
    def idsList(self,ids):
        assetsList = Assets.objects.filter(id__in=ids)
        return self.query(assetsList)   
    
    def tags(self,tags,request=None):
        assetsList = [ ds.aid for ds in Tags_Server_Assets.objects.filter(tid=tags)]
        if request:return self.query(self.query_user_assets(request, assetsList))       
        return self.query(assetsList)         
    
    def service(self,service,request=None):    
        assetsList = Assets.objects.filter(business=service,assets_type__in=["server","vmser","switch","route"])    
        if request:return self.query(self.query_user_assets(request, assetsList))       
        return self.query(assetsList)         

    def group(self,group,request=None):   
        assetsList = Assets.objects.filter(group=group,assets_type__in=["server","vmser","switch","route"])       
        if request:return self.query(self.query_user_assets(request, assetsList))       
        return self.query(assetsList)  
    
    def inventory_group(self,inventory_group,request=None):
        try:
            inventoryGroup = Deploy_Inventory_Groups.objects.get(id=inventory_group)
            assetsIds =  [ ds.server for ds in Deploy_Inventory_Groups_Server.objects.filter(groups=inventoryGroup)]
        except Exception as ex:
            logger.error(msg="获取资产组失败:{ex}".format(ex=ex))  
            assetsIds = [0]    
        assetsList = Assets.objects.filter(id__in=assetsIds)      
        if request:return self.query(self.query_user_assets(request, assetsList))       
        return self.query(assetsList)  
    
    def custom(self,server,request=None):
        if isinstance(server,str):server = server.split(',')
        assetsList = Assets.objects.filter(id_in=server,assets_type__in=["server","vmser","switch","route"])
        if request:return self.query(self.query_user_assets(request, assetsList))       
        return self.query(assetsList)         
        
    def serverList(self,args=None):
        return self.query(self.assetsList())
        
    def query(self,assetsList):    
        dataList = []                            
        for assets in assetsList:          
            if hasattr(assets,'server_assets'):
                try:
                    dataList.append({"id":assets.id,"ip":assets.server_assets.ip,})#"project":project,"service":service,"status":assets.status,"mark":assets.mark})                       
                except Exception as ex:
                    logger.warn(msg="id:{assets}, error:{ex}".format(assets=assets.id,ex=ex))                    
            elif hasattr(assets,'network_assets'):
                try:
                    dataList.append({"id":assets.id,"ip":assets.network_assets.ip,})#"project":project,"service":service,"status":assets.status,"mark":assets.mark})                       
                except Exception as ex:
                    logger.warn(msg="id:{assets}, error:{ex}".format(assets=assets.id,ex=ex))  
        return dataList                   
    
    def get_networkcard(self,assets):
        dataList = []
        for nt in NetworkCard_Assets.objects.filter(assets_id=assets.id):
            dataList.append(self.convert_to_dict(nt))
        return dataList  
    
    def get_disk(self,assets):        
        dataList = []
        for dk in Disk_Assets.objects.filter(assets_id=assets.id):
            dataList.append(self.convert_to_dict(dk))
        return dataList  
    
    def get_ram(self,assets):
        dataList = []
        for rm in Ram_Assets.objects.filter(assets_id=assets.id):
            dataList.append(self.convert_to_dict(rm))
        return dataList 
    
    def get_server(self,assets):
        server_data = {}
        if hasattr(assets,'server_assets'):
            server_data = self.convert_to_dict(assets.server_assets)
            try:
                server_data['line'] = Line_Assets.objects.get(id=assets.server_assets.line).line_name
            except Exception as ex:
                server_data['line'] = '未知'        
            try:
                server_data['raid'] = Line_Assets.objects.get(id=assets.server_assets.raid).raid_name
            except Exception as ex:
                server_data['raid'] = '未知'  
        return server_data         
              
    def get_network(self,assets):
        data = {}
        if hasattr(assets,'network_assets'):
            data['network'] = self.convert_to_dict(assets.network_assets)                   
        return data
    
    def assets_tags(self,assets,request=None):
        dataList = []
        for ds in Tags_Server_Assets.objects.filter(aid=assets):
            data = {}
            data['tags_name'] = ds.tid.tags_name
            data['id'] = ds.tid.id
            dataList.append(data)
        return  dataList         
          
    def info(self,id):
        assets = self.assets(id)
        data = dict()
        if assets:
            data = self.convert_to_dict(assets)
            try:
                data['group'] = Structure.objects.get(id=assets.group).text
            except Exception as ex:
                data['group'] = '未知'
            try:
                data['buy_user'] = User.objects.get(id=assets.buy_user).username
            except Exception as ex:
                data['buy_user'] = '未知'
            try:
                data['put_zone'] = Zone_Assets.objects.get(id=assets.put_zone).zone_name
            except Exception as ex:
                data['put_zone'] = '未知'
            try:
                data['idc'] = Idc_Assets.objects.get(id=assets.idc).zone_name
            except Exception as ex:
                data['idc'] = '未知'                
            try:
                data['project'] = Project_Assets.objects.get(id=assets.project).project_name
            except Exception as ex:
                data['project'] = '未知'
            try:
                data['service'] = Service_Assets.objects.get(id=assets.business).service_name
            except Exception as ex:
                data['service'] = '未知'          
            try:
                data['cabinet'] = Cabinet_Assets.objects.get(id=assets.cabinet).cabinet_name
            except Exception as ex:
                data['cabinet'] = '未知'                      
            data['networkcard'] = self.get_networkcard(assets)
            data['disk'] = self.get_disk(assets) 
            data['ram'] = self.get_ram(assets)   
            data['server'] = self.get_server(assets)
            data['network'] = self.get_network(assets)  
            data['tags'] = self.assets_tags(assets)      
        return data      
    
    def read_import_file(self,filename):
        bk = xlrd.open_workbook(filename)
        dataList = []
        try:
            server = bk.sheet_by_name("server")
            net = bk.sheet_by_name("net")
            for i in range(1,server.nrows):
                dataList.append(server.row_values(i)) 
            for i in range(1,net.nrows):
                dataList.append(net.row_values(i))     
        except Exception as ex:
            logger.warn(msg="读取导入的资产文件失败: {ex}".format(ex=str(ex)))  
            return "读取导入的资产文件失败: {ex}".format(ex=str(ex))    
        return dataList      
    
    def import_assets(self,filename):
        dataList = self.read_import_file(filename)
        if isinstance(dataList, str):return dataList
        #获取服务器列表
        for data in dataList:
            assets = {
                      'assets_type':data[0],
                      'name':data[1],
                      'sn':data[2],
                      'buy_user':int(data[5]),
                      'management_ip':data[6],
                      'manufacturer':data[7],
                      'model':data[8],
                      'provider':data[9],
                      'status':int(data[10]),
                      'put_zone':int(data[11]),
                      'group':int(data[12]),
#                       'project':int(data[13]),
#                       'business':int(data[14]),
                      }
            if data[3]:assets['buy_time'] = xlrd.xldate.xldate_as_datetime(data[3],0)
            if data[4]:assets['expire_date'] = xlrd.xldate.xldate_as_datetime(data[4],0)
            if assets.get('assets_type') in ['vmser','server']:
                server_assets = {
                          'ip':data[13],
                          'keyfile':data[14],
                          'username':data[15],
                          'passwd':data[16],
                          'hostname':data[17],
                          'port':data[18],
                          'raid':data[19],
                          'line':data[20],
                          } 
            else:
                net_assets = {
                            'ip':data[13],
                            'bandwidth':data[14],
                            'port_number': data[15],
                            'firmware':data[16],
                            'cpu':data[17],
                            'stone':data[18],
                            'configure_detail': data[19]                              
                              }                                                  
            count = Assets.objects.filter(name=assets.get('name')).count()
            if count == 1:
                assetsObj = Assets.objects.get(name=assets.get('name'))
                Assets.objects.filter(name=assets.get('name')).update(**assets)
                try:
                    if assets.get('assets_type') in ['vmser','server']:
                        Server_Assets.objects.filter(assets=assetsObj).update(**server_assets)
                    elif assets.get('assets_type') in ['switch','route','printer','scanner','firewall','storage','wifi']:
                        Network_Assets.objects.filter(assets=assetsObj).update(**net_assets)
                except  Exception as ex:
                    logger.warn(msg="批量更新资产失败: {ex}".format(ex=str(ex)))
                    return "批量更新资产失败: {ex}".format(ex=str(ex))
            else:
                try:
                    assetsObj = Assets.objects.create(**assets)   
                except Exception as ex:
                    logger.warn(msg="批量写入资产失败: {ex}".format(ex=str(ex)))
                    return "批量写入资产失败: {ex}".format(ex=str(ex))
                if assetsObj:
                    try:  
                        if assets.get('assets_type') in ['vmser','server']:
                            Server_Assets.objects.create(assets=assetsObj,**server_assets)
                        elif assets.get('assets_type') in ['switch','route','printer','scanner','firewall','storage','wifi']:
                            Network_Assets.objects.create(assets=assetsObj,**net_assets)                          
                    except Exception as ex:
                        logger.warn(msg="批量更新资产失败: {ex}".format(ex=str(ex)))                        
                        assetsObj.delete()
                        return "批量更新资产失败: {ex}".format(ex=str(ex))
               


class AssetsCount(object):
    def __init__(self):
        super(AssetsCount, self).__init__()  
        self.dataList = []
        
    def groupAssets(self):
        try:
            return [ {"count":ds.count,"name":ds.text} for ds in Group.objects.raw("""SELECT t1.id,count(*) as count,t1.text from opsmanage_structure t1, opsmanage_assets t2 WHERE t2.group = t1.id GROUP BY t1.id ORDER BY count desc limit 5;""")]
        except Exception as ex:
            logger.error(msg="统计业务组主机资产失败:{ex}".format(ex=ex))
        return self.dataList


    def idcAssets(self):
        try:
            return [ {"count":ds.count,"idc_name":ds.idc_name} for ds in Idc_Assets.objects.raw("""SELECT t1.id,count(*) as count,t1.idc_name from opsmanage_idc_assets t1, opsmanage_assets t2 WHERE t2.idc = t1.id GROUP BY t2.idc""")]
        except Exception as ex:
            logger.error(msg="统计机房主机资产失败:{ex}".format(ex=ex))
        return self.dataList 

    def statusAssets(self):
        try:
            return [ {"count":ds.count,"status":ds.status} for ds in Assets.objects.raw("""SELECT id,count(*) as count,status from opsmanage_assets GROUP BY status;""")]  
        except Exception as ex:
            logger.error(msg="统计状态主机资产失败:{ex}".format(ex=ex))
        return self.dataList 
    
    def typeAssets(self):
        try:
            return [ {"count":ds.count,"assets_type":ds.assets_type} for ds in Assets.objects.raw("""SELECT id,count(*)  as count,assets_type from opsmanage_assets GROUP BY assets_type;""")] 
        except Exception as ex:
            logger.error(msg="统计资产类型失败:{ex}".format(ex=ex))
        return self.dataList     
    
    def databasesAssets(self):
        dataList = []
        try:
            for ds in DataBase_MySQL_Server_Config.objects.raw("""SELECT id,count(*) as count,db_env from opsmanage_database_server_config GROUP BY db_env;"""):
                if ds.db_env == "beta":dataList.append({"count":ds.count,"db_env":"测试环境"})
                else:
                    dataList.append({"count":ds.count,"db_env":"生产环境"})           
            return dataList 
        except Exception as ex:
            logger.error(msg="统计数据库类型失败:{ex}".format(ex=ex))
        return self.dataList      
    
    def appsAssets(self):
        dataList = []
        try:
            for ds in Project_Config.objects.raw("""SELECT id,count(id)  as count,project_env from opsmanage_project_config GROUP BY project_env;"""):
                if ds.project_env == "sit":dataList.append({"count":ds.count,"project_env":"测试环境"})
                elif ds.project_env == "qa":dataList.append({"count":ds.count,"project_env":"灰度环境"})
                else:dataList.append({"count":ds.count,"project_env":"生产环境"})               
            return dataList 
        except Exception as ex:
            logger.error(msg="统计代码发布类型失败:{ex}".format(ex=ex))
        return self.dataList  
    
    def tagsAssets(self):
        dataList = []
        try:
            for ds in Tags_Assets.objects.all():
                data = {}
                data["count"] = Tags_Server_Assets.objects.filter(tid=ds).count()
                data["tags_name"] = ds.tags_name
                dataList.append(data)
            return dataList
        except Exception as ex:
            logger.error(msg="统计代码发布类型失败:{ex}".format(ex=ex))
        return dataList             
    
    
    def assetsCount(self):
        return {"name":"总资产","count":Assets.objects.all().count()}
    
    def tagsCount(self):
        return {"name":"资产标签","count":Tags_Assets.objects.all().count()}
    
    def appsCount(self):
        return {"name":"代码部署","count":Project_Config.objects.all().count()}
        
    def dbCount(self):
        return {"name":"数据库","count":DataBase_MySQL_Server_Config.objects.all().count()}
    
    def scriptCount(self):
        return {"name":"部署脚本","count":Deploy_Script.objects.all().count()}
    
    def playbookCount(self):
        return {"name":"部署剧本","count":Deploy_Playbook.objects.all().count()}
    
    def navbarCount(self):
        return {"name":"站内导航","count":Nav_Type_Number.objects.all().count()}
    
    def schedCount(self):
        return {"name":"计划任务","count":Cron_Config.objects.all().count()}
    
    def wikiCount(self):
        return {"name":"运维文档","count":Post.objects.all().count()}
    
    def userCount(self):
        return {"name":"用户统计","count":User.objects.all().count()}
    
    def otherCount(self):
        return {"name":"三方接入","count":Nav_Third_Number.objects.all().count()}
    
    def ordersCount(self):
        return {"name":"总工单数","count":Order_System.objects.all().count()}
        
    def allCount(self):
        return [
                self.assetsCount(),
                self.tagsCount(),
                self.appsCount(),
                self.dbCount(),
                self.schedCount(),
                self.scriptCount(),
                self.playbookCount(),
                self.navbarCount(),
                self.wikiCount(),
                self.userCount(),
                self.otherCount(),
                self.ordersCount()
                ]
    
class AssetsSource(object):
    def __init__(self):
        super(AssetsSource,self).__init__()
        self.fList = []
        self.sList = [] 
        self.resource = [] 
    
    def serverList(self):
        serverList = []
        for assets in Assets.objects.filter(assets_type__in=["server","vmser","switch","route"]):
            try:
                service =  Service_Assets.objects.get(id=assets.business).service_name
            except:
                service = '未知'
            try:
                project =  Project_Assets.objects.get(id=assets.project).project_name
            except:
                project = '未知'                
            if hasattr(assets,'server_assets'):
                serverList.append({"id":assets.id,"ip":assets.server_assets.ip,'project':project,'service':service})
            elif hasattr(assets,'network_assets'):
                serverList.append({"id":assets.id,"ip":assets.network_assets.ip,'project':project,'service':service})
        return  serverList   
    
    def queryAssetsByIp(self,ipList):       
        for ip in ipList:
            data = {}
            server = Server_Assets.objects.filter(ip=ip).count()
            network = Network_Assets.objects.filter(ip=ip).count()
            if server > 0:
                try:
                    server_assets = Server_Assets.objects.get(ip=ip)
                    self.sList.append(server_assets.ip)
                    data["ip"] = server_assets.ip
                    data["port"] = int(server_assets.port)
                    data["username"] = server_assets.username
                    data["hostname"] = server_assets.ip
                    data["sudo_passwd"] = server_assets.sudo_passwd
                    if server_assets.keyfile != 1:data["password"] =  server_assets.passwd  
                    elif server_assets.keyfile_path:
                        data["private_key"] = server_assets.keyfile_path                                      
                except Exception as ex:
                    logger.warn(msg="server_id:{assets}, error:{ex}".format(assets=server_assets.id,ex=ex))
                if server_assets.assets.host_vars:
                    try:                         
                        for k,v in eval(server_assets.assets.host_vars).items():
                            if k not in ["ip", "port", "username", "password","ip"]:data[k] = v 
                    except Exception as ex:
                        logger.warn(msg="资产: {assets},转换host_vars失败:{ex}".format(assets=server_assets.assets.id,ex=ex))                                                
            elif network > 0:
                try:    
                    network_assets = Network_Assets.objects.get(ip=ip)
                    self.sList.append(network_assets.ip)
                    data["ip"] = network_assets.ip
                    data["port"] = int(network_assets.port)
                    data["password"] = network_assets.passwd,
                    data["username"] = network_assets.username
                    data["hostname"] = network_assets.ip
                    data["sudo_passwd"] = network_assets.sudo_passwd
                    data["connection"] = 'local'
                except Exception as ex:
                    logger.warn(msg="network_id:{assets}, error:{ex}".format(assets=server_assets.id,ex=ex))  
                if network_assets.assets.host_vars:
                    try:                         
                        for k,v in eval(network_assets.assets.host_vars).items():
                            if k not in ["ip", "port", "username", "password","ip"]:data[k] = v 
                    except Exception as ex:
                        logger.warn(msg="资产: {assets},转换host_vars失败:{ex}".format(assets=network_assets.assets.id,ex=ex))              
            self.resource.append(data)
        return  self.sList, self.resource           

    def allowcator(self, sub, request):
        if hasattr(self,sub):
            func= getattr(self,sub)
            return func(request)
        else:
            logger.error(msg="AssetsSource没有{sub}方法".format(sub=sub))       
            return [],[]

    def query_user_assets(self,request,assetsList):
        if request.user.is_superuser:
            return  assetsList   
        assets_list =[ das.assets for das in User_Server.objects.filter(user=request.user,assets_id__in=[ ds.id for ds in assetsList ])]          
        return assets_list        
            
    def custom(self,request):
        if request.method == 'POST':
            if request.POST.getlist('server',[]):serverList = request.POST.getlist('server')
            elif request.POST.getlist('custom',[]):serverList = request.POST.getlist('custom')
            else:serverList = request.POST.getlist('server[]')
        elif request.method == 'PUT':
            serverList = QueryDict(request.body).getlist('server[]')
        assetsList = Assets.objects.select_related().filter(id__in=serverList)
        return self.source(self.query_user_assets(request, assetsList))    
    
    def tags(self,request):
        assetsList = [ ds.aid for ds in Tags_Server_Assets.objects.filter(tid=request.POST.get('tags'))]
        return self.source(self.query_user_assets(request, assetsList))      
    
    def group(self,request):
        assetsList = Assets.objects.select_related().filter(group=request.POST.get('group'),assets_type__in=["server","vmser","switch","route"])
        return self.source(self.query_user_assets(request, assetsList))
                
    def business(self,request):
        try:
            business = Business_Tree_Assets.objects.get(id=request.POST.get('business'))
            assetsList = business.assets_set.all()
        except:
            assetsList = []
        return self.source(self.query_user_assets(request, assetsList))
    
    def idSourceList(self, ids):
        assetsList = Assets.objects.filter(id__in=ids)
        return self.source(assetsList)        
    
    def idSource(self, ids):
        assetsList = Assets.objects.filter(id=ids)
        return self.source(assetsList)
                
    def source(self, assetsList):                             
        for assets in assetsList:
            data = {}
            if hasattr(assets,'server_assets'):
                try:
                    self.sList.append(assets.server_assets.ip)
                    data["ip"] = assets.server_assets.ip
                    data["port"] = int(assets.server_assets.port)
                    data["username"] = assets.server_assets.username
                    data["hostname"] = assets.server_assets.ip
                    data["sudo_passwd"] = assets.server_assets.sudo_passwd                    
                    if assets.server_assets.keyfile == 0:
                        data["password"] =  assets.server_assets.passwd   
                    elif assets.server_assets.keyfile_path:
                        data["private_key"] = assets.server_assets.keyfile_path                      
                except Exception as ex:
                    logger.warn(msg="id:{assets}, error:{ex}".format(assets=assets.id,ex=ex))                    
            elif hasattr(assets,'network_assets'):
                try:
                    self.sList.append(assets.network_assets.ip)
                    data["ip"] = assets.network_assets.ip
                    data["port"] = int(assets.network_assets.port)
                    data["password"] = assets.network_assets.passwd
                    data["hostname"] = assets.network_assets.ip
                    data["username"] = assets.network_assets.username
                    data["sudo_passwd"] = assets.network_assets.sudo_passwd
                    data["connection"] = 'local'
                except Exception as ex:
                    logger.warn(msg="id:{assets}, error:{ex}".format(assets=assets.id,ex=ex)) 
                      
            if assets.host_vars:
                try: 
                    data["vars"] = json.loads(assets.host_vars)
                except Exception as ex:
                    logger.warn(msg="资产: {assets},转换host_vars失败:{ex}".format(assets=assets.id,ex=ex)) 
                    
            self.resource.append(data)
        return self.sList, self.resource
        
    def inventory(self,inventory):
        sList = []
        resource = {} 
        groups = ''
        try:
            inventory = Deploy_Inventory.objects.get(id=inventory)
        except Exception as ex: 
            logger.warn(msg="资产组查询失败：{id}".format(id=inventory,ex=ex))
        for ds in inventory.inventory_group.all():
            resource[ds.group_name] = {}
            hosts = []
            for ser in ds.inventory_group_server.all():
                assets =  Assets.objects.get(id=ser.server)
                data = {}
                if hasattr(assets,'server_assets'):
                    try:
                        serverIp = assets.server_assets.ip
                        data["ip"] = serverIp
                        data["port"] = int(assets.server_assets.port)
                        data["username"] = assets.server_assets.username
                        data["hostname"] = assets.server_assets.ip
                        data["sudo_passwd"] = assets.server_assets.sudo_passwd                        
                        if assets.server_assets.keyfile != 1:data["password"] =  assets.server_assets.passwd
                        elif assets.server_assets.keyfile_path:
                            data["private_key"] = assets.server_assets.keyfile_path                         
                    except Exception as ex:
                        logger.warn(msg="id:{assets}, error:{ex}".format(assets=assets.id,ex=ex))                     
                elif hasattr(assets,'network_assets'):                 
                    try:
                        serverIp = assets.network_assets.ip
                        data["ip"] = serverIp
                        data["port"] = int(assets.network_assets.port)
                        data["password"] = assets.network_assets.passwd,
                        data["username"] = assets.network_assets.username
                        data["hostname"] = assets.network_assets.ip
                        data["sudo_passwd"] = assets.network_assets.sudo_passwd
                        data["connection"] = 'local'
                    except Exception as ex:
                        logger.warn(msg="id:{assets}, error:{ex}".format(assets=assets.id,ex=ex))
                if assets.host_vars:
                    try:                         
                        for k,v in eval(assets.host_vars).items():
                            if k not in ["ip", "port", "username", "password","ip"]:data[k] = v
                    except Exception as ex:
                        logger.warn(msg="资产: {assets},转换host_vars失败:{ex}".format(assets=assets.id,ex=ex))                        
                if serverIp not in sList:sList.append(serverIp)
                hosts.append(data)
            resource[ds.group_name]['hosts'] = hosts 
            groups +=  ds.group_name + ','
            try:
                if ds.ext_vars:resource[ds.group_name]['vars'] = eval(ds.ext_vars)  
            except Exception as ex: 
                logger.warn(msg="资产组变量转换失败: {id} {ex}".format(id=inventory,ex=ex))
                resource[ds.group_name]['vars'] = None
        return sList, resource,groups   
    
    def inventory_groups(self,request):   
        sList = []
        resource = {} 
        group_name = ''
        try:
            inventoryGroup = Deploy_Inventory_Groups.objects.get(id=request.POST.get('inventory_groups'))
            group_name = inventoryGroup.group_name
        except Exception as ex: 
            logger.warn(msg="资产组查询失败：{id}".format(id=request.POST.get('inventory_groups'),ex=ex))
        resource[inventoryGroup.group_name] = {}
        hosts = []
        for ser in inventoryGroup.inventory_group_server.all():
            assets =  Assets.objects.get(id=ser.server)
            data = {}
            if hasattr(assets,'server_assets'):
                try:
                    serverIp = assets.server_assets.ip
                    data["ip"] = serverIp
                    data["port"] = int(assets.server_assets.port)
                    data["username"] = assets.server_assets.username
                    data["hostname"] = assets.server_assets.ip
                    data["sudo_passwd"] = assets.server_assets.sudo_passwd                        
                    if assets.server_assets.keyfile != 1:data["password"] =  assets.server_assets.passwd
                    elif assets.server_assets.keyfile_path:
                        data["private_key"] = assets.server_assets.keyfile_path                     
                except Exception as ex:
                    logger.warn(msg="id:{assets}, error:{ex}".format(assets=assets.id,ex=ex))                     
            elif hasattr(assets,'network_assets'):                 
                try:
                    serverIp = assets.network_assets.ip
                    data["ip"] = serverIp
                    data["port"] = int(assets.network_assets.port)
                    data["password"] = assets.network_assets.passwd
                    data["hostname"] = assets.network_assets.ip
                    data["username"] = assets.network_assets.username
                    data["sudo_passwd"] = assets.network_assets.sudo_passwd
                    data["connection"] = 'local'
                except Exception as ex:
                    logger.warn(msg="id:{assets}, error:{ex}".format(assets=assets.id,ex=ex))
            if assets.host_vars:
                try:                         
                    for k,v in eval(assets.host_vars).items():
                        if k not in ["ip", "port", "username", "password","ip"]:data[k] = v
                except Exception as ex:
                    logger.warn(msg="资产: {assets},转换host_vars失败:{ex}".format(assets=assets.id,ex=ex))                        
            if serverIp not in sList:sList.append(serverIp)
            hosts.append(data)
            resource[group_name]['hosts'] = hosts 
            try:
                if inventoryGroup.ext_vars:resource[group_name]['vars'] = eval(inventoryGroup.ext_vars)  
            except Exception as ex: 
                logger.warn(msg="资产组变量转换失败: {id} {ex}".format(id=request.POST.get('inventory_groups'),ex=ex))
                resource[inventoryGroup.group_name]['vars'] = None
        return sList, resource        
    
    def get_data(self,request):
        if request.POST.get('model')=='batch':
            sList,resource = self.idSourceList(ids=request.POST.getlist('ids[]'))
            ANS = ANSRunner(resource)  
            ANS.run_model(host_list=sList,module_name='setup',module_args="") 
            data = ANS.handle_cmdb_data(ANS.get_model_result())    
                    
        elif request.POST.get('model')=='collector':
            sList,resource = self.idSource(ids=request.POST.get('ids'))
            ANS = ANSRunner(resource)  
            ANS.run_model(host_list=sList,module_name='setup',module_args="")  
            data = ANS.handle_cmdb_data(ANS.get_model_result())    
                   
        else:
            sList,resource = self.idSource(ids=request.POST.get('ids'))
            ANS = ANSRunner(resource)  
            ANS.run_model(host_list=sList,module_name='crawHw',module_args="")  
            data = ANS.handle_cmdb_crawHw_data(ANS.get_model_result())                          
        return data,ANS.get_model_result()
    
    def batch(self, request):  
        return self.collector(request)
    
    def collector(self, request):  
        sList,fList = [], []
        data, result = self.get_data(request) 
        if data:                  
            for ds in data:
                status = ds.get('status')
                sip = ds.get('ip') 
                if status == 0:
                    assets = Server_Assets.objects.get(ip=ds.get('ip')).assets
                    assets.model = ds.get('model')
                    assets.save()
                    try:
                        Server_Assets.objects.filter(ip=ds.get('ip')).update(cpu_number=ds.get('cpu_number'),kernel=ds.get('kernel'),
                                                                              selinux=ds.get('selinux'),hostname=ds.get('hostname'),
                                                                              system=ds.get('system'),cpu=ds.get('cpu'),
                                                                              disk_total=ds.get('disk_total'),cpu_core=ds.get('cpu_core'),
                                                                              swap=ds.get('swap'),ram_total=ds.get('ram_total'),
                                                                              vcpu_number=ds.get('vcpu_number')
                                                                            )
                        if sip not in sList:sList.append(sip)
                    except Exception:
                        if sip not in fList:fList.append(sip) 
                    for nk in ds.get('nks'):
                        macaddress = nk.get('macaddress')
                        count = NetworkCard_Assets.objects.filter(assets=assets,macaddress=macaddress).count()
                        if count > 0:
                            try:
                                NetworkCard_Assets.objects.filter(assets=assets,macaddress=macaddress).update(assets=assets,device=nk.get('device'),
                                                                                                                   ip=nk.get('address'),module=nk.get('module'),
                                                                                                                   mtu=nk.get('mtu'),active=nk.get('active'))
                            except Exception as ex:
                                logger.warn(msg="更新服务器网卡资产失败: {ex}".format(ex=str(ex)))
                        else:
                            try:
                                NetworkCard_Assets.objects.create(assets=assets,device=nk.get('device'),
                                                              macaddress=nk.get('macaddress'),
                                                              ip=nk.get('address'),module=nk.get('module'),
                                                              mtu=nk.get('mtu'),active=nk.get('active'))
                            except Exception as ex:
                                logger.warn(msg="更新写入服务器网卡资产失败: {ex}".format(ex=str(ex)))                         
                else:
                    if sip not in fList:fList.append(sip) 
                    logger.warn(msg="获取主机信息失败: {ex}".format(ex=str(result)))   
            return fList,sList
    
    
    def crawHw(self,request):  
        sList,fList = [],[]
        data,result = self.get_data(request)     
        assets = Assets.objects.get(id=request.POST.get('ids')) 
        if data:
            for ds in data:
                sip = ds.get('ip')
                if ds.get('mem_info'):
                    for mem in ds.get('mem_info'):
                        if Ram_Assets.objects.filter(assets=assets,device_slot=mem.get('slot')).count() > 0:
                            try:
                                Ram_Assets.objects.filter(assets=assets,device_slot=mem.get('slot')).update(
                                                        device_slot=mem.get('slot'),device_model=mem.get('serial'),
                                                        device_brand= mem.get('manufacturer'),device_volume=mem.get('size'),
                                                        device_status=1
                                                        )
                                if sip not in sList:sList.append(sip)
                            except Exception as ex:
                                if sip not in fList:fList.append(sip) 
                                logger.warn(msg="更新写入内存资产失败: {ex}".format(ex=str(ex)))  
                        else:
                            try:
                                Ram_Assets.objects.create(device_slot=mem.get('slot'),device_model=mem.get('serial'),
                                                         device_brand= mem.get('manufacturer'),device_volume=mem.get('size'),
                                                         device_status=1,assets=assets
                                                         )
                                if sip not in sList:sList.append(sip)
                            except Exception as ex:
                                if sip not in fList:fList.append(sip) 
                                logger.warn(msg="更新写入内存资产失败: {ex}".format(ex=str(ex)))  
                if ds.get('disk_info'):
                    for disk in ds.get('disk_info'):
                        if Disk_Assets.objects.filter(assets=assets,device_slot=disk.get('slot')).count() > 0:
                            try:
                                Disk_Assets.objects.filter(assets=assets,device_slot=disk.get('slot')).update(
                                                        device_serial=disk.get('serial'),device_model=disk.get('model'),
                                                        device_brand= disk.get('manufacturer'),device_volume=disk.get('size'),
                                                        device_status=1
                                                         )
                                if sip not in sList:sList.append(sip)
                            except Exception as ex:
                                if sip not in fList:fList.append(sip) 
                                logger.warn(msg="更新写入硬盘资产失败: {ex}".format(ex=str(ex)))  
                        else:                           
                            try:
                                Disk_Assets.objects.create(device_serial=disk.get('serial'),device_model=disk.get('model'),
                                                         device_brand= disk.get('manufacturer'),device_volume=disk.get('size'),
                                                         device_status=1,assets=assets,device_slot=disk.get('slot')
                                                         )
                                if sip not in sList:sList.append(sip)
                            except Exception as ex:
                                if sip not in fList:fList.append(sip)
                                logger.warn(msg="更新写入硬盘资产失败: {ex}".format(ex=str(ex))) 
            return fList, sList
        else:
            return result,[]

class AssetsAnsible(DataHandle):
    def __init__(self):
        super(AssetsAnsible,self).__init__()      
        
    def allowcator(self,sub,request):
        if hasattr(self,sub):
            func= getattr(self,sub)
            return func(request)
        else:
            logger.error(msg="AssetsAnsible没有{sub}方法".format(sub=sub))       
            
              
    def query_user_assets(self,request,assetsList):
        if request.get('is_superuser'):
            return  assetsList   
        assets_list =[ das.assets for das in User_Server.objects.filter(user=request.get('user'),assets_id__in=[ ds.id for ds in assetsList ])]          
        return assets_list        
            
    def custom(self,request):
        custom = request.get('custom')
        if not custom:
            logger.warn(msg="主机不能为空");
            return [],[]

        assetsList = Assets.objects.select_related().filter(id__in=request.get('custom'))
        return self.source(self.query_user_assets(request, assetsList))    
    
    def tags(self,request):
        tags = request.get('tags')
        if not tags:
            logger.warn(msg="资产标签不能为空");
            return [],[]

        assetsList = [ ds.aid for ds in Tags_Server_Assets.objects.filter(tid=request.get('tags'))]
        return self.source(self.query_user_assets(request, assetsList))      
    
    def group(self,request):
        group = request.get('group')
        if not group:
            logger.warn(msg="使用组不能为空");
            return [],[]

        assetsList = Assets.objects.select_related().filter(group=request.get('group'),assets_type__in=["server","vmser","switch","route"])
        return self.source(self.query_user_assets(request, assetsList))
                
    def business(self,request):
        business = request.get('business')
        if not business:
            logger.warn(msg="业务不能为空");
            return [],[]

        try:
            business = Business_Tree_Assets.objects.get(id=request.get('business'))
            assetsList = business.assets_set.all()
        except:
            assetsList = []
        return self.source(self.query_user_assets(request, assetsList))
    
    def inventory_groups(self,request):   
        sList = []
        resource = {} 
        group_name = ''

        inventory_group = request.get('inventory_groups')
        if not inventory_group:
            logger.warn(msg="主机组不能为空");
            return sList, resource

        try:
            inventoryGroup = Deploy_Inventory_Groups.objects.get(id=inventory_group)
            group_name = inventoryGroup.group_name
        except Exception as ex: 
            logger.warn(msg="资产组查询失败：{id}".format(id=request.get('inventory_groups'),ex=ex))
        resource[inventoryGroup.group_name] = {}
        hosts = []
        for ser in inventoryGroup.inventory_group_server.all():
            assets =  Assets.objects.get(id=ser.server)
            data = {}
            if hasattr(assets,'server_assets'):
                try:
                    serverIp = assets.server_assets.ip
                    data["ip"] = serverIp
                    data["port"] = int(assets.server_assets.port)
                    data["username"] = assets.server_assets.username
                    data["hostname"] = assets.server_assets.ip
                    data["sudo_passwd"] = assets.server_assets.sudo_passwd                        
                    if assets.server_assets.keyfile != 1:data["password"] =  assets.server_assets.passwd
                    elif assets.server_assets.keyfile_path:
                        data["private_key"] = assets.server_assets.keyfile_path                     
                except Exception as ex:
                    logger.warn(msg="id:{assets}, error:{ex}".format(assets=assets.id,ex=ex))                     
            elif hasattr(assets,'network_assets'):                 
                try:
                    serverIp = assets.network_assets.ip
                    data["ip"] = serverIp
                    data["port"] = int(assets.network_assets.port)
                    data["password"] = assets.network_assets.passwd
                    data["hostname"] = assets.network_assets.ip
                    data["username"] = assets.network_assets.username
                    data["sudo_passwd"] = assets.network_assets.sudo_passwd
                    data["connection"] = 'local'
                except Exception as ex:
                    logger.warn(msg="id:{assets}, error:{ex}".format(assets=assets.id,ex=ex))
            if assets.host_vars:
                try:                         
                    for k,v in eval(assets.host_vars).items():
                        if k not in ["ip", "port", "username", "password","ip"]:data[k] = v
                except Exception as ex:
                    logger.warn(msg="资产: {assets},转换host_vars失败:{ex}".format(assets=assets.id,ex=ex))                        
            if serverIp not in sList:sList.append(serverIp)
            hosts.append(data)
            resource[group_name]['hosts'] = hosts 
            try:
                if inventoryGroup.ext_vars:resource[group_name]['vars'] = eval(inventoryGroup.ext_vars)  
            except Exception as ex: 
                logger.warn(msg="资产组变量转换失败: {id} {ex}".format(id=request.get('inventory_groups'),ex=ex))
                resource[inventoryGroup.group_name]['vars'] = None
        return sList, resource     
                
    def source(self,assetsList): 
        sList,resource = [],[]                            
        for assets in assetsList:
            data = {}
            if hasattr(assets,'server_assets'):
                try:
                    sList.append(assets.server_assets.ip)
                    data["ip"] = assets.server_assets.ip
                    data["port"] = int(assets.server_assets.port)
                    data["username"] = assets.server_assets.username
                    data["hostname"] = assets.server_assets.ip
                    data["sudo_passwd"] = assets.server_assets.sudo_passwd                   
                    if assets.server_assets.keyfile == 0:data["password"] =  assets.server_assets.passwd  
                    elif assets.server_assets.keyfile_path:
                        data["private_key"] = assets.server_assets.keyfile_path                                            
                except Exception as ex:
                    logger.warn(msg="id:{assets}, error:{ex}".format(assets=assets.id,ex=ex))                    
            elif hasattr(assets,'network_assets'):
                try:
                    sList.append(assets.network_assets.ip)
                    data["ip"] = assets.network_assets.ip
                    data["port"] = int(assets.network_assets.port)
                    data["password"] = assets.network_assets.passwd
                    data["hostname"] = assets.network_assets.ip
                    data["username"] = assets.network_assets.username
                    data["sudo_passwd"] = assets.network_assets.sudo_passwd
                    data["connection"] = 'local'
                except Exception as ex:
                    logger.warn(msg="id:{assets}, error:{ex}".format(assets=assets.id,ex=ex)) 
                    
            if assets.host_vars:
                try:                      
                    data["vars"] = json.loads(assets.host_vars)
                except Exception as ex:
                    logger.warn(msg="资产: {assets},转换host_vars失败:{ex}".format(assets=assets.id,ex=ex)) 
                    
            resource.append(data)
        return sList,resource    
        
ASSETS_COUNT_RBT = AssetsCount()    
ASSETS_BASE = AssetsBase()
# ASSETS_SOURCE = AssetsSource()