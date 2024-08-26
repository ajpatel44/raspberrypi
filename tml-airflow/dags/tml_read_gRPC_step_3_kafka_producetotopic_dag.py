import maadstml
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime
from airflow.decorators import dag, task
import grpc
from concurrent import futures
import time
import tml_grpc_pb2_grpc as pb2_grpc
import tml_grpc_pb2 as pb2
import tsslogging
import sys
import os

sys.dont_write_bytecode = True
##################################################  gRPC SERVER ###############################################
# This is a gRPCserver that will handle connections from a client
# There are two endpoints you can use to stream data to this server:
# 1. jsondataline -  You can POST a single JSONs from your client app. Your json will be streamed to Kafka topic.
# 2. jsondataarray -  You can POST JSON arrays from your client app. Your json will be streamed to Kafka topic.

######################################## USER CHOOSEN PARAMETERS ########################################
default_args = {
  'owner' : 'Sebastian Maurice', # <<< *** Change as needed
  'enabletls': 1, # <<< *** 1=connection is encrypted, 0=no encryption
  'microserviceid' : '', # <<< ***** leave blank
  'producerid' : 'iotsolution',  # <<< *** Change as needed
  'topics' : 'iot-raw-data', # *************** This is one of the topic you created in SYSTEM STEP 2
  'identifier' : 'TML solution',  # <<< *** Change as needed
  'gRPC_Port' : 9001,  # <<< ***** replace with gRPC port i.e. this gRPC server listening on port 9001 
  'delay' : 7000, # << ******* 7000 millisecond maximum delay for VIPER to wait for Kafka to return confirmation message is received and written to topic
  'topicid' : -999, # <<< ********* do not modify          
  'start_date': datetime (2023, 1, 1),  # <<< *** Change as needed   
  'retries': 1,  # <<< *** Change as needed   
    
}
    
######################################## DO NOT MODIFY BELOW #############################################

# Instantiate your DAG
@dag(dag_id="tml_read_gRPC_step_3_kafka_producetotopic_dag", default_args=default_args, tags=["tml_read_gRPC_step_3_kafka_producetotopic_dag"], start_date=datetime(2023, 1, 1), schedule=None,catchup=False)
def startproducingtotopic():
  # This sets the lat/longs for the IoT devices so it can be map
  def empty():
      pass

dag = startproducingtotopic()

VIPERTOKEN=""
VIPERHOST=""
VIPERPORT=""
    
class TmlprotoService(pb2_grpc.TmlprotoServicer):

  def __init__(self, *args, **kwargs):
    pass

  def GetServerResponse(self, request, context):

    # get the string from the incoming request
    message = request.message
    readata(message)
    #result = f'Hello I am up and running received "{message}" message from you'
    #result = {'message': result, 'received': True}

    #return pb2.MessageResponse(**result)

def serve(**context):
    repo=tsslogging.getrepo()   
    tsslogging.tsslogit("gRPC producing DAG in {}".format(os.path.basename(__file__)), "INFO" )                     
    tsslogging.git_push("/{}".format(repo),"Entry from {}".format(os.path.basename(__file__)),"origin")            
    ti = context['task_instance']
    ti.xcom_push(key='PRODUCETYPE',value='gRPC')
    ti.xcom_push(key='TOPIC',value=default_args['topics'])
    ti.xcom_push(key='PORT',value=default_args['gRPC_Port'])
    ti.xcom_push(key='IDENTIFIER',value=default_args['identifier'])

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_UnaryServicer_to_server(UnaryService(), server)
    server.add_insecure_port("[::]:{}".format(default_args['gRPC_Port']))
    server.start()
    server.wait_for_termination()

def gettmlsystemsparams(**context):
  global VIPERTOKEN
  global VIPERHOST
  global VIPERPORT

  VIPERTOKEN = context['ti'].xcom_pull(task_ids='solution_task_getparams',key="VIPERTOKEN")
  VIPERHOST = context['ti'].xcom_pull(task_ids='solution_task_getparams',key="VIPERHOST")
  VIPERPORT = context['ti'].xcom_pull(task_ids='solution_task_getparams',key="VIPERPORT")
    

def producetokafka(value, tmlid, identifier,producerid,maintopic,substream,args):
 inputbuf=value     
 topicid=args['topicid']

 # Add a 7000 millisecond maximum delay for VIPER to wait for Kafka to return confirmation message is received and written to topic 
 delay=args['delay']
 enabletls = args['enabletls']
 identifier = args['identifier']

 try:
    result=maadstml.viperproducetotopic(VIPERTOKEN,VIPERHOST,VIPERPORT,maintopic,producerid,enabletls,delay,'','', '',0,inputbuf,substream,
                                        topicid,identifier)
 except Exception as e:
    print("ERROR:",e)

def readdata(valuedata):
  args = default_args
  # MAin Kafka topic to store the real-time data
  maintopic = args['topics']
  producerid = args['producerid']

  try:
      producetokafka(valuedata.strip(), "", "",producerid,maintopic,"",args)
      # change time to speed up or slow down data   
      time.sleep(0.15)
  except Exception as e:
      print(e)  
      pass  
  
def startproducing(**context):
       gettmlsystemsparams(context)
       serve(context)
