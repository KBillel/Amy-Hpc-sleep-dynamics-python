import numpy as np
import pandas as pd
import neuroseries as nts
import scipy.io
import sys
from progressbar import ProgressBar
import time
import pickle
import matplotlib.pyplot as plt

from IPython.display import clear_output

import os

def sessions():
    return pd.read_csv('Z:/All-Rats/Billel/session_indexing.csv',sep = ';')

def current_session(path_local):
    
    #Author : BK 08/20
    #Input Path to the session to load
    #output : True if loading was done correctly
    #Variable are stored in global variables.
    
        #Create Global variable that allow for all function to know in wich session we are this usefull only for variable that are going to be recurentyly used. Do not overuse this functionnality as it can add inconstansies. 
    global session, path, rat, day

    
    session_index = pd.read_csv('Z:/All-Rats/Billel/session_indexing.csv',sep = ';')
   
    path = path_local
    session = path.split('\\')[2]
    rat = session_index['Rat'][session_index['Path'] == path].values
    day = session_index['Day'][session_index['Path'] == path].values
    
    print('Rat : ' + str(int(rat)) + ' on day : ' + str(int(day)))
    print('Working with session ' + session + ' @ ' + path)
    
    
    os.chdir(path)
    
   
    
    return True

def batch(func,verbose = False):
    
    #Author : BK
    #Date : 08/20
    
    #Input Function
    #Output : Output of the function
    
    #This function batch over all rat / all session and return output of the functions.
    
    
    t = time.time()
    session_index = pd.read_csv('Z:/All-Rats/Billel/session_indexing.csv',sep = ';')
    pbar = ProgressBar()
    
    error = []
    output_dict = {}
    for path in pbar(session_index['Path']):
#         os.chdir(path)
        session = path.split('\\')[2]
        print('Loading Data from ' + session)
        
        try:
            output = func(path)
            output_dict.update({session:output})
            if not verbose: clear_output()
        except:
            error.append(session)
            print('Error in session ' + session)
            if not verbose: clear_output()
    print('Batch finished in ' + str(time.time() - t))
    
    if error:
        print('Some session were not processed correctly')
        print(error)
        print(len(error)/len(session_index['Path'])*100,'%')
        
    return output_dict
    
def get_raw_data_directory(raw_data_directory = "\\\AGNODICE\IcyBox"):
    return raw_data_directory

def get_session_path(session_name):
    #Author : Anass
    rat = session_name[0:5] #"Rat08"
    rat_path = os.path.join(get_raw_data_directory(),rat)
    session_path = os.path.join(rat_path,session_name)
    return session_path


def pos():
    #BK : 04/08/2020
    #Return a NeuroSeries DataFrame of position whith the time as index
    
#     session_path = get_session_path(session_name)
    pos_clean = scipy.io.loadmat(path + "/posClean.mat")['posClean']
    return nts.TsdFrame(t = pos_clean[:,0],d = pos_clean[:,1:],columns = ['x','y'],time_units = 's')

def states():
    #BK : 17/09/2020
    #Return a dict with variable from States.
#     if session_path == 0 : session_path = get_session_path(session_name)
    states = scipy.io.loadmat(path + '/States.mat')
    
    useless  = ['__header__','__version__','__globals__']
    for u in useless:
        del states[u]
    states_ = {}
    for state in states:
        states_.update({state:nts.IntervalSet(states[state][:,0],states[state][:,1],time_units = 's')})
        
    return states_

def loadSpikeData(path, index=None, fs = 20000):  
    ### Adapted from Viejo github https://github.com/PeyracheLab/StarterPack/blob/master/python/wrappers.py
    ### Modified by BK 06/08/20
    ### Modification are explicit with comment
    """
    if the path contains a folder named /Analysis, 
    the script will look into it to load either
        - SpikeData.mat saved from matlab
        - SpikeData.h5 saved from this same script
    if not, the res and clu file will be loaded 
    and an /Analysis folder will be created to save the data
    Thus, the next loading of spike times will be faster
    Notes :
        If the frequency is not givne, it's assumed 20kH
    Args:
        path : string

    Returns:
        dict, array    
    """
    
#     try session:
#     except: print('Did you load a session first?')
    
    
    if not os.path.exists(path):
        print("The path "+path+" doesn't exist; Exiting ...")
        sys.exit()

    files = os.listdir(path)
    # Changed 'clu' to '.clu.' same for res as in our dataset we have file containing the word clu that are not clu files
    clu_files     = np.sort([f for f in files if '.clu.' in f and f[0] != '.'])
    res_files     = np.sort([f for f in files if '.res.' in f and f[0] != '.'])
    
    # Changed because some files have weird names in GG dataset because of some backup on clu/res files
    # Rat10-20140627.clu.10.07.07.2014.15.41 for instance
    
    clu_files = clu_files[[len(i) < 22 for i in clu_files]]
    res_files = res_files[[len(i) < 22 for i in res_files]]
    

    clu1         = np.sort([int(f.split(".")[-1]) for f in clu_files])
    clu2         = np.sort([int(f.split(".")[-1]) for f in res_files])
    
#     if len(clu_files) != len(res_files) or not (clu1 == clu2).any():
#         print("Not the same number of clu and res files in "+path+"; Exiting ...")
#         sys.exit()
#   Commented this because in GG dataset their .clu.12.54.21.63 files that mess up everything ...
    
    count = 0
    spikes = []
    basename = clu_files[0].split(".")[0]
    idx_clu_returned = []
    for i, s in zip(range(len(clu_files)),clu1):
        clu = np.genfromtxt(os.path.join(path,basename+'.clu.'+str(s)),dtype=np.int32)[1:]
        print('Loading '+basename + '.clu.' + str(s))
        if np.max(clu)>1:
            res = np.genfromtxt(os.path.join(path,basename+'.res.'+str(s)))
            tmp = np.unique(clu).astype(int)
            idx_clu = tmp[tmp>1]
            idx_clu_returned.extend(idx_clu) # Allow to return the idx of each neurons on it's shank. Very important for traceability
            idx_col = np.arange(count, count+len(idx_clu))       
            tmp = pd.DataFrame(index = np.unique(res)/fs,
                                columns = pd.MultiIndex.from_product([[s],idx_col]),
                                data = 0, 
                                dtype = np.uint16)
            
            for j, k in zip(idx_clu, idx_col):
                tmp.loc[res[clu==j]/fs,(s,k)] = np.uint16(k+1)
            spikes.append(tmp)
            count+=len(idx_clu)

    #Returning a list instead of dict in order to use list of bolean.
    toreturn =  []
    shank = []
    for s in spikes:
        shank.append(s.columns.get_level_values(0).values)
        sh = np.unique(shank[-1])[0]
        for i,j in s:
            toreturn.append(nts.Tsd(t=s[(i,j)].replace(0,np.nan).dropna().index.values, time_units = 's'))
            #To return was change to nts.Tsd instead of nts.Ts as it has bug for priting (don't know where it is coming from)

    del spikes
    shank = np.hstack(shank)
    return np.array(toreturn,dtype = 'object'), np.array([shank, idx_clu_returned]).T #idx_clu is returned in order to keep indexing consistent with Matlab code.

def loadLFP(path, n_channels=90, channel=64, frequency=1250.0, precision='int16'):
    #From Guillaume Viejo
    import neuroseries as nts
    if type(channel) is not list:
        f = open(path, 'rb')
        startoffile = f.seek(0, 0)
        endoffile = f.seek(0, 2)
        bytes_size = 2		
        n_samples = int((endoffile-startoffile)/n_channels/bytes_size)
        duration = n_samples/frequency
        interval = 1/frequency
        f.close()
        with open(path, 'rb') as f:
            print('opening')
            data = np.fromfile(f, np.int16).reshape((n_samples, n_channels))[:,channel]
            timestep = np.arange(0, len(data))/frequency
        return nts.Tsd(timestep, data, time_units = 's')
    elif type(channel) is list:
        f = open(path, 'rb')
        startoffile = f.seek(0, 0)
        endoffile = f.seek(0, 2)
        bytes_size = 2

        n_samples = int((endoffile-startoffile)/n_channels/bytes_size)
        duration = n_samples/frequency
        f.close()
        with open(path, 'rb') as f:
            data = np.fromfile(f, np.int16).reshape((n_samples, n_channels))[:,channel]
            timestep = np.arange(0, len(data))/frequency
        return nts.TsdFrame(timestep, data, time_units = 's')

def lfp(start, stop, n_channels=90, channel=64, frequency=1250.0, precision='int16'):
    
    p = session+".lfp"
    print('Load LFP from ' + p)
    # From Guillaume viejo
    import neuroseries as nts	
    bytes_size = 2		
    start_index = int(start*frequency*n_channels*bytes_size)
    stop_index = int(stop*frequency*n_channels*bytes_size)
    fp = np.memmap(p, np.int16, 'r', start_index, shape = (stop_index - start_index)//bytes_size)
    data = np.array(fp).reshape(len(fp)//n_channels, n_channels)

    if type(channel) is not list:
        timestep = np.arange(0, len(data))/frequency+start
        return nts.Tsd(timestep, data[:,channel], time_units = 's')
    elif type(channel) is list:
        timestep = np.arange(0, len(data))/frequency+start
        return nts.TsdFrame(timestep, data[:,channel], time_units = 's')

