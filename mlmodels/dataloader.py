# -*- coding: utf-8 -*-
"""

https://www.tensorflow.org/api_docs/python/tf/compat/v1
tf.compat.v1   IS ALL TF 1.0

tf.compat.v2    iS TF 2.0

Typical user workflow

def get_dataset(data_pars):
    loader = DataLoader(data_pars)
    loader.compute()
    data = loader.get_data()
    [print(x.shape) for x in data]
    return data





"""
#### System utilities
import os
import sys
import inspect
from urllib.parse import urlparse
import json
from importlib import import_module
import pandas as pd
import numpy as np
from collections.abc import MutableMapping
from functools import partial

# possibly replace with keras.utils.get_file down the road?
#### It dowloads from HTTP from Dorpbox, ....  (not urgent)
# from cli_code.cli_download import Downloader


from sklearn.model_selection import train_test_split
import cloudpickle as pickle


#########################################################################
#### mlmodels-internal imports
from mlmodels.util import load_callable_from_dict, load_callable_from_uri, path_norm, path_norm_dict, log

from mlmodels.preprocess.generic import pandasDataset, NumpyDataset

#########################################################################
#### Specific packages   ##### Be ware of tensorflow version
#### I fpossible, we dont use to have dependance on tensorflow, torch, ...


"""  Not used
import tensorflow as tf
import torch
import torchtext
import keras

import tensorflow.data
"""


VERBOSE = 0 
DATASET_TYPES = ["csv_dataset", "text_dataset", "NumpyDataset", "pandasDataset"]



#########################################################################
def pickle_load(file):
    return pickle.load(open(file, " r"))


def pickle_dump(t, **kwargs):
    with open(kwargs["path"], "wb") as fi:
        pickle.dump(t, fi)
    return t


def image_dir_load(path):
    return ImageDataGenerator().flow_from_directory(path)


def batch_generator(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx : min(ndx + n, l)]


def _validate_data_info(self, data_info):
    dataset = data_info.get("dataset", None)
    if not dataset:
        raise KeyError("Missing dataset key in the dataloader.")

    dataset_type = data_info.get("dataset_type", None)

    if dataset_type and dataset_type not in DATASET_TYPES:
        raise Exception(f"Unknown dataset type {dataset_type}")
    return True

    self.path          = path
    self.dataset_type  = dataset_type
    self.test_size     = data_info.get("test_size", None)
    self.generator     = data_info.get("generator", False)
    self.batch_size    = int(data_info.get("batch_size", 1))

    self.col_Xinput    = data_info.get("col_Xinput", None)
    self.col_Yinput    = data_info.get("col_Yinput", None)
    self.col_miscinput = data_info.get("col_miscinput", None)


def _check_output_shape(self, inter_output, shape, max_len):
    case = 0
    if isinstance(inter_output, tuple):
        if not isinstance(inter_output[0], dict):
            case = 1
        else:
            case = 2
    if isinstance(inter_output, dict):
        if not isinstance(tuple(inter_output.values())[0], dict):
            case = 3
        else:
            case = 4
    # max_len enforcement
    if max_len is not None:
        try:
            if case == 0:
                inter_output = inter_output[0:max_len]
            if case == 1:
                inter_output = [o[0:max_len] for o in inter_output]
            if case == 3:
                inter_output = {
                    k: v[0:max_len] for k, v in inter_output.items()
                }
        except:
            pass
    # shape check
    if shape is not None:
        if (
            case == 0
            and hasattr(inter_output, "shape")
            and tuple(shape) != inter_output.shape
        ):
            raise Exception(
                f"Expected shape {tuple(shape)} does not match shape data shape {inter_output.shape[1:]}"
            )
        if case == 1:
            for s, o in zip(shape, inter_output):
                if hasattr(o, "shape") and tuple(s) != o.shape[1:]:
                    raise Exception(
                        f"Expected shape {tuple(shape)} does not match shape data shape {inter_output.shape[1:]}"
                    )
        if case == 3:
            for s, o in zip(shape, tuple(inter_output.values())):
                if hasattr(o, "shape") and tuple(s) != o.shape[1:]:
                    raise Exception(
                        f"Expected shape {tuple(shape)} does not match shape data shape {inter_output.shape[1:]}"
                    )
    self.output_shape = shape
    return inter_output



def get_dataset_type(x) :
    from mlmodel.process.generic import PandasDataset, NumpyDataset, Dataset, kerasDataset  #Pytorch
    from mlmodel.process.generic import DataLoader  ## Pytorch


    if isinstance(x, PandasDataset  ) : return "PandasDataset"
    if isinstance(x, NumpyDataset  ) : return "NumpyDataset"
    if isinstance(x, Dataset  ) : return "pytorchDataset"



"""

data_pars --> Dataloader.py  :
  sequence of pre-processors item
       uri, args
       return some objects in a sequence way.



"data_pars": {  
 "data_info": { 
                  "name" : "text_dataset",   "data_path": "dataset/nlp/WIKI_QA/" , 
                  "train": true
                  } 
         },
 

"preprocessors": [ 
                {  "uri" : "mlmodels.preprocess.generic.:train_test_val_split",
                    "arg" : {   "split_if_exists": true, "frac": 0.99, "batch_size": 64,  "val_batch_size": 64,
                                    "input_path" :    "dataset/nlp/WIKIQA_singleFile/" ,
                                    "output_path" :  "dataset/nlp/WIKIQA" ,   
                                    "format" : "csv"
                               },
                    "output_type" :  "file_csv"
                } ,  


             {  "name" : "loader"  ,
                "uri" :  "mlmodels.model_tch.matchzoo:WIKI_QA_loader",
                "arg" :  {  "name" : "text_dataset",   
                                        "data_path": "dataset/nlp/WIKI_QA/"   ,
                                         "data_pack"  : "",   "mode":"pair",  "num_dup":2,   "num_neg":1,
                                        "batch_size":20,     "resample":true,  
                                        "sort":false,   "callbacks":"PADDING"
                                      },
                 "output_type" :  "pytorch_dataset"
             } ]
}


"""



class DataLoader:

    default_loaders = {
        ".csv": {"uri": "pandas::read_csv", "pass_data_pars":False},
        ".npy": {"uri": "numpy::load", "pass_data_pars":False},
        ".npz": {"uri": "np:load", "arg": {"allow_pickle": True}, "pass_data_pars":False},
        ".pkl": {"uri": "dataloader::pickle_load", "pass_data_pars":False},

        "image_dir": {"uri": "dataloader::image_dir_load", "pass_data_pars":False},
    }
    _validate_data_info = _validate_data_info
    _check_output_shape = _check_output_shape
    
    def __init__(self, data_pars):
        self.final_output             = {}
        self.internal_states          = {}
        self.data_info                = data_pars['data_info']
        self.preprocessors            = data_pars.get('preprocessors', [])
        # self.final_output_type        = data_pars['output_type']



    def check(self):
        # Validate data_info
        self._validate_data_info(self.data_info)

        input_type_prev = "file"   ## HARD CODE , Bad

        for preprocessor in self.preprocessors:
            uri = preprocessor.get("uri", None)
            if not uri:
                print(f"Preprocessor {preprocessor} missing uri")


            ### Compare date type for COMPATIBILITY
            input_type = preprocessor.get("input_type", "")   ### Automatic ???
            if input_type != input_type_prev :
                print(f"Mismatch input / output data type {preprocessor} ")                  

            input_type_prev = preprocessor.get('output_type', "")
       

    def compute(self, docheck=1):
        if docheck :
            self.check()


        input_tmp = None
        for preprocessor in self.preprocessors:
            uri  = preprocessor["uri"]
            args = preprocessor.get("args", {})
            print("URL: ",uri, args)


            preprocessor_func = load_callable_from_uri(uri)
            if inspect.isclass(preprocessor_func):
                ### Should match PytorchDataloader, KerasDataloader, PandasDataset, ....
                ## A class : muti-steps compute
                cls_name = preprocessor_func.__name__
                print("cls_name :", cls_name)



                if cls_name in DATASET_TYPES:  # dataset object
                    obj_preprocessor = preprocessor_func(**args, data_info=self.data_info)


                    if cls_name == "pandasDataset" or cls_name == "NumpyDataset": # get dataframe/numpyarray instead of pytorch dataset
                        out_tmp = obj_preprocessor.get_data()
                    else:
                        out_tmp = obj_preprocessor


                else:  # pre-process object defined in preprocessor.py
                    obj_preprocessor = preprocessor_func(**args)
                    obj_preprocessor.compute(input_tmp)
                    out_tmp = obj_preprocessor.get_data()




            else:
                ### Only a function, not a Class : Directly COMPUTED.

                # print("input_tmp: ",input_tmp['X'].shape,input_tmp['y'].shape)
                # print("input_tmp: ",input_tmp.keys())
                pos_params = inspect.getfullargspec(preprocessor_func)[0]
                print("postional parameteres : ", pos_params)
                if isinstance(input_tmp, (tuple, list)) and len(input_tmp) > 0 and len(pos_params) == 0:
                    out_tmp = preprocessor_func(*input_tmp, **args)

                elif pos_params == ['data_info']:
                    # function with postional parmater data_info >> get_dataset_torch(data_info, **args)
                    out_tmp = preprocessor_func(data_info=self.data_info, **args)
                else:
                    out_tmp = preprocessor_func(input_tmp, **args)



            ## Be careful of Very Large Dataset, it will not work not to save ALL 
            ## Save internal States
            if preprocessor.get("internal_states", None):
                for internal_state in preprocessor.get("internal_states", None):
                    if isinstance(out_tmp, dict):
                        self.internal_states[internal_state] = out_tmp[internal_state]

            input_tmp = out_tmp
        self.final_output = out_tmp

    def get_data(self):
        return self.final_output, self.internal_states



##########################################################################################################
### Test functions
def split_xy_from_dict(out, **kwargs):
    X_c    = kwargs.get('col_Xinput',[])
    y_c    = kwargs.get('col_yinput',[])
    X      = [out[n] for n in X_c]
    y      = [out[n] for n in y_c]
    return (*X,*y)


def test_run_model():
    from mlmodels.models import test_module

    # param_pars = {
    #     "choice": "json",
    #     "config_mode": "test",
    #     "data_path": "dataset/json/refactor/03_nbeats_dataloader.json",
    # }
    # test_module("model_tch/03_nbeats_dataloader.py", param_pars)

    param_pars = {
        "choice": "json",
        "config_mode": "test",
        "data_path": "dataset/json/refactor/namentity_crm_bilstm_dataloader_new.json",
    }
    test_module("model_keras/namentity_crm_bilstm_dataloader.py", param_pars)



def test_dataloader(path='dataset/json/refactor/'):
    refactor_path = path_norm( path )
    # data_pars_list = [(f,json.loads(open(refactor_path+f).read())['test']['data_pars']) for f in os.listdir(refactor_path)]
    

    data_pars_list = [f for f in os.listdir(refactor_path)  if not os.path.isdir( refactor_path + "/" + f)  ]
    print(data_pars_list)

    """
    l1  =  [
            # path_norm('dataset/json/refactor/torchhub.json' )
            path_norm('dataset/json/refactor/namentity_crm_bilstm_dataloader_new.json' )
            ,path_norm('dataset/json/refactor/namentity_crm_bilstm_dataloader_new.json' )
    ]
    data_pars_list = l1
    """

    data_pars_list  =  [

            # path_norm('dataset/json/refactor/namentity_crm_bilstm_dataloader_new.json' )
            path_norm('dataset/json/refactor/torchhub_cnn_dataloader.json' ),
            path_norm('dataset/json/refactor/model_list_CIFAR.json' ),
            path_norm('dataset/json/refactor/resnet34_benchmark_mnist.json' ),
            path_norm('dataset/json/refactor/keras_textcnn.json'),
            path_norm('dataset/json/refactor/namentity_crm_bilstm_new.json' )

    ] 

    for f in data_pars_list:
        try :
          #f  = refactor_path + "/" + f

          if os.path.isdir(f) : continue

          print("\n" *5 , "#" * 100)
          print(  f)
          

          print("#"*5, " Load JSON data_pars") 
          d = json.loads(open( f ).read())
          data_pars = d['test']['data_pars']
          data_pars = path_norm_dict( data_pars)
          print(data_pars)
          

          print( "\n", "#"*5, " Load DataLoader ") 
          loader    = DataLoader(data_pars)


          print("\n", "#"*5, " compute DataLoader ")           
          loader.compute()
          print(loader.get_data())

        except Exception as e :
          print("Error", f,  e)


####################################################################################################
def cli_load_arguments(config_file=None):
    """
        Load CLI input, load config.toml , overwrite config.toml by CLI Input
    """
    import argparse
    p = argparse.ArgumentParser()
    def add(*k, **kw):
        p.add_argument(*k, **kw)

    add("--config_file" , default=None                     , help="Params File")
    add("--config_mode" , default="test"                   , help="test/ prod /uat")
    add("--log_file"    , help="File to save the logging")

    add("--do"          , default="test"                   , help="what to do test or search")

    ###### model_pars
    add("--path", default='dataset/json/refactor/', help="name of the model for --do test")

    ###### data_pars
    # add("--data_path", default="dataset/GOOG-year_small.csv", help="path of the training file")

    ###### out params
    # add('--save_path', default='ztest/search_save/', help='folder that will contain saved version of best model')

    args = p.parse_args()
    # args = load_config(args, args.config_file, args.config_mode, verbose=0)
    return args


def main():
    arg = cli_load_arguments()

    if arg.do == "test":
        test_dataloader('dataset/json/refactor/')   

    if arg.do == "test_run_model":
       test_run_model()


if __name__ == "__main__":
   VERBOSE =1  
   main() 
    
    
 



    
"""
    
    

#########################################################################
def pickle_load(file):
    return pickle.load(open(f, " r"))


def pickle_dump(t,path):
    pickle.dump(t, open(path, "wb" ))


def image_dir_load(path):
    return ImageDataGenerator().flow_from_directory(path)


def batch_generator(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx : min(ndx + n, l)]


def _interpret_input_pars(self, input_pars):
    try:
        path = input_pars["path"]
    except KeyError:
        raise Exception("Missing path key in the dataloader.")

    path_type = input_pars.get("path_type", None)
    if path_type is None:
        if os.path.isfile(path):
            path_type = "file"
        if os.path.isdir(path):
            path_type = "dir"

        if urlparse(path).scheme != "":
            path_type = "url"
            download_path = input_pars.get("download_path", "./")

        if path_type == "dropbox":
            dropbox_download(path)
            path_type = "file"

        if path_type is None:
            raise Exception(f"Path type for {path} is undeterminable")

    elif path_type != "file" and path_type != "dir" and path_type != "url":
        raise Exception("Unknown location type")

    file_type = input_pars.get("file_type", None)
    if file_type is None:
        if path_type == "dir":
            file_type = "image_dir"
        elif path_type == "file":
            file_type = os.path.splitext(path)[1]
        else:
            if path[-1] == "/":
                raise Exception("URL must target a single file.")
            file_type = os.path.splittext(path.split("/")[-1])[1]

    self.path = path
    self.path_type = path_type
    self.file_type = file_type
    self.test_size = input_pars.get("test_size", None)
    self.generator = input_pars.get("generator", False)
    if self.generator:
        try:
            self.batch_size = int(input_pars.get("batch_size", 1))
        except:
            raise Exception("Batch size must be an integer")
    self.col_Xinput = input_pars.get("col_Xinput", None)
    self.col_Yinput = input_pars.get("col_Yinput", None)
    self.col_miscinput = input_pars.get("col_miscinput", None)
    validation_split_function = [
        {"uri": "sklearn.model_selection::train_test_split", "arg": {}},
        "test_size",
    ]
    self.validation_split_function = input_pars.get(
        "split_function", validation_split_function
    )


def _check_output_shape(self, inter_output, shape, max_len):
    case = 0
    if isinstance(inter_output, tuple):
        if not isinstance(inter_output[0], dict):
            case = 1
        else:
            case = 2
    if isinstance(inter_output, dict):
        if not isinstance(tuple(inter_output.values())[0], dict):
            case = 3
        else:
            case = 4
    # max_len enforcement
    if max_len is not None:
        try:
            if case == 0:
                inter_output = inter_output[0:max_len]
            if case == 1:
                inter_output = [o[0:max_len] for o in inter_output]
            if case == 3:
                inter_output = {
                    k: v[0:max_len] for k, v in inter_output.items()
                }
        except:
            pass
    # shape check
    if shape is not None:
        if (
            case == 0
            and hasattr(inter_output, "shape")
            and tuple(shape) != inter_output.shape
        ):
            raise Exception(
                f"Expected shape {tuple(shape)} does not match shape data shape {inter_output.shape[1:]}"
            )
        if case == 1:
            for s, o in zip(shape, inter_output):
                if hasattr(o, "shape") and tuple(s) != o.shape[1:]:
                    raise Exception(
                        f"Expected shape {tuple(shape)} does not match shape data shape {inter_output.shape[1:]}"
                    )
        if case == 3:
            for s, o in zip(shape, tuple(inter_output.values())):
                if hasattr(o, "shape") and tuple(s) != o.shape[1:]:
                    raise Exception(
                        f"Expected shape {tuple(shape)} does not match shape data shape {inter_output.shape[1:]}"
                    )
    self.output_shape = shape
    return inter_output


class DataLoader:

    default_loaders = {
        ".csv": {"uri": "pandas::read_csv", "pass_data_pars":False},
        ".npy": {"uri": "numpy::load", "pass_data_pars":False},
        ".npz": {"uri": "np:load", "arg": {"allow_pickle": True}, "pass_data_pars":False},
        ".pkl": {"uri": "dataloader::pickle_load", "pass_data_pars":False},
        "image_dir": {"uri": "dataloader::image_dir_load", "pass_data_pars":False},
    }
    _validate_data_info = _validate_data_info
    _check_output_shape = _check_output_shape
    
    def __init__(self, data_pars):
        self.final_output             = {}
        self.internal_states          = {}
        self.data_info                = data_pars['data_info']
        self.preprocessors            = data_pars.get('preprocessors', [])

    def compute(self):
        # Validate data_info
        self._validate_data_info(self.data_info)

        input_tmp = None
        for preprocessor in self.preprocessors:
            uri = preprocessor.get("uri", None)
            if not uri:
                raise Exception(f"Preprocessor {preprocessor} missing uri")

            name = preprocessor.get("name", None)
            args = preprocessor.get("args", {})

            preprocessor_func = load_callable_from_uri(uri)
            if name == "loader":
                out_tmp = preprocessor_func(self.path, **args)
            elif name == "saver":  # saver do not return output
                preprocessor_func(self.path, **args)
            else:
                if inspect.isclass(preprocessor_func):
                    obj_preprocessor = preprocessor_func(**args)
                    obj_preprocessor.compute(input_tmp)
                    out_tmp = obj_preprocessor.get_data()
                else:
                    if isinstance(input_tmp, (tuple, list)):
                        out_tmp = preprocessor_func(*input_tmp[:2], **args)
                    else:
                        out_tmp = preprocessor_func(input_tmp, **args)
            if preprocessor.get("internal_states", None):
                for internal_state in preprocessor.get("internal_states", None):
                    if isinstance(out_tmp, dict):
                        self.internal_states[internal_state] = out_tmp[internal_state]

            input_tmp = out_tmp
        self.final_output = out_tmp

    def get_data(self):
        return self.final_output, self.internal_states



### Test functions
def split_xy_from_dict(out,data_pars):
    X_c    = data_pars['input_pars'].get('col_Xinput',[])
    y_c    = data_pars['input_pars'].get('col_yinput',[])
    misc_c = data_pars['input_pars'].get('col_miscinput',[])
    X      = [out[n] for n in X_c]
    y      = [out[n] for n in y_c]
    misc   = [out[n] for n in misc_c]
    return (*X,*y,*misc)


if __name__ == "__main__":
    from mlmodels.models import test_module

    # param_pars = {
    #     "choice": "json",
    #     "config_mode": "test",
    #     "data_path": "dataset/json/refactor/03_nbeats_dataloader.json",
    # }
    # test_module("model_tch/03_nbeats_dataloader.py", param_pars)

    param_pars = {
        "choice": "json",
        "config_mode": "test",
        "data_path": "dataset/json/refactor/namentity_crm_bilstm_dataloader_new.json",
    }
    test_module("model_keras/namentity_crm_bilstm_dataloader.py", param_pars)

    """
    
    
    
    
    
