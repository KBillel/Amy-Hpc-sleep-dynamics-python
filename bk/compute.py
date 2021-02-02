import numpy as np
import neuroseries as nts
from tqdm import tqdm
import os
import scipy.stats

def freezing_intervals(speed,threshold, mode='single_speed',clean = False, t_merge = 0.5,t_drop = 1,save = False):
    
    """
        BK 8/11/20
        Input 
            speed: speed vector as output by bk.compute.speed (not yet implemented. But it's an nts.frame)
            treshold: arbritary units
    """
    
    
    if mode.lower() =='single_speed':
        fs =  1/scipy.stats.mode(np.diff(speed.as_units('s').index)).mode[0]
        freezing = speed.values<threshold
        
        if freezing[0] == 1: freezing[0] = 0
        if freezing[-1] == 1: freezing = np.append(freezing,0)

        dfreeze = np.diff(freezing.astype(np.int8))
        start = np.where(dfreeze == 1)[0]/fs + speed.as_units('s').index[0]
        end = np.where(dfreeze == -1)[0]/fs + speed.as_units('s').index[0]
    elif mode.lower() == 'multiple_speed':
        fs =  1/scipy.stats.mode(np.diff(speed.as_units('s').index)).mode[0]
        freezing = np.array((np.sum(speed.as_units('s'),axis = 1))/speed.shape[1] < threshold)
        
        if freezing[0] == 1: freezing[0] = 0
        if freezing[-1] == 1: freezing = np.append(freezing,0)

        dfreeze = np.diff(freezing.astype(np.int8))
        start = np.where(dfreeze == 1)[0]/fs + speed.as_units('s').index[0]
        end = np.where(dfreeze == -1)[0]/fs + speed.as_units('s').index[0]
    elif mode.lower() == 'pca':
        print('not implanted')
    else:
        print('Mode not recognized')
        return False
    freezing_intervals = nts.IntervalSet(start,end,time_units = 's')
    if clean:
        freezing_intervals = freezing_intervals.merge_close_intervals(t_merge,time_units = 's').drop_short_intervals(t_drop,time_units = 's')
        
    
    if save:
        np.save('freezing_intervals',freezing_intervals,allow_pickle = True)
    
    return freezing_intervals

def freezing_video(video_path,output_file,tf,freezing_intervals):
    
    """
        video_path : path to the video to be displaying
        outputfile : path to the video to written
        tf : vector of time containing timing of each frame
        freezing intervals : Intervals when the animal is freezing (as nts.Interval_Set)
    """
    import cv2

    if os.path.exists(output_file):
        print(output_file,'already exist, please delete manually')
        return
    
    tf = nts.Ts(tf,time_units='s')
    freezing_frames = np.where(freezing_intervals.in_interval(tf)>=0)[0]
    fs =  1/scipy.stats.mode(np.diff(tf.as_units('s').index)).mode[0]
    cap  = cv2.VideoCapture(video_path)
    frame_width = int(cap.get(3))
    frame_height = int(cap.get(4))
    
    nf = 0
    out = cv2.VideoWriter(output_file,cv2.VideoWriter_fourcc('M','J','P','G'), fs, (frame_width,frame_height))
    while True:
        
        ret,frame = cap.read()
        if ret == True:
            if nf in freezing_frames: frame = cv2.circle(frame,(25,25),10,(0,0,255),20)

            cv2.imshow(video_path,frame)
            out.write(frame)
            if cv2.waitKey(1) & 0xFF == ord('q'): 
                break
            nf +=1
        else:
            break
    cap.release()
    out.release()
    
    return True

def tone_intervals(digital_tone, Fs = 20000, t_merge = 1, t_drop = 1):
    """
        Input : digitalin channel of tone
        Return, nts.IntervalSet for tones, (and Fq of tones)
    """
    edges = TTL_edges(digital_tone,Fs)
    
    tone_intervals = nts.IntervalSet(edges.start,edges.end).merge_close_intervals(t_merge,time_units = 's').drop_short_intervals(t_drop,time_units = 's')
    
    return tone_intervals
    

def TTL_edges(TTL,Fs = 20000):
    if isinstance(TTL[0],(np.bool_,bool)):
        TTL = list(map(int,TTL))
    
    if TTL[0] == 1: TTL[0] = 0
    if TTL[-1] == 1: TTL.append(0)
        
    diff_TTL = np.diff(TTL)
    
    t_start = np.where(diff_TTL == 1)[0]
    t_end = np.where(diff_TTL == -1)[0]
    
    edges = nts.IntervalSet(t_start/Fs,t_end/Fs,time_units = 's')
    return edges
    
def TTL_to_intervals(TTL,Fs = 20000):
    if isinstance(TTL[0],(np.bool_,bool)):
        TTL = list(map(int,TTL))
    
    
    diff_TTL = np.diff(TTL)
    
    t_start = np.where(diff_TTL == 1)[0]
    t_end = np.where(diff_TTL == -1)[0]
    t_TTL = np.array([np.mean(interval) for interval in zip(t_start,t_end)])
    
    
    return (t_start/Fs,t_end/Fs)


def TTL_to_times(TTL,Fs = 20000):
    
    if isinstance(TTL[0],(np.bool_,bool)):
        TTL = list(map(int,TTL))
    
    diff_TTL = np.diff(TTL)
    
    t_start = np.where(diff_TTL == 1)[0]
    t_end = np.where(diff_TTL == -1)[0]
    t_TTL = np.array([np.mean(interval) for interval in zip(t_start,t_end)])
    
    return t_TTL/Fs

def old_speed(pos,value_gaussian_filter,pixel = 0.43):
    x_speed = np.diff(pos.as_units('s')['x'])/np.diff(pos.as_units('s').index)
    y_speed = np.diff(pos.as_units('s')['y'])/np.diff(pos.as_units('s').index)

    v = np.sqrt(x_speed**2 + y_speed**2)*pixel
    
    v = scipy.ndimage.gaussian_filter1d(v,value_gaussian_filter,axis=0)
    v = nts.Tsd(t = pos.index.values[:-1],d = v)
    
    return v
def speed(pos,value_gaussian_filter, columns_to_drop=None):
    
    body = []
    for i in pos:
        body.append(i[0])
    body = np.unique(body)
    
    all_speed = np.empty((len(pos)-1,5))
    i = 0
    for b in body:
        x_speed = np.diff(pos.as_units('s')[b]['x'])/np.diff(pos.as_units('s').index)
        y_speed = np.diff(pos.as_units('s')[b]['y'])/np.diff(pos.as_units('s').index)
    
        v = np.sqrt(x_speed**2 + y_speed**2)
        all_speed[:,i] = v
        i +=1
    all_speed = scipy.ndimage.gaussian_filter1d(all_speed,value_gaussian_filter,axis=0)
    all_speed = nts.TsdFrame(t = pos.index.values[:-1],d = all_speed,columns = body)
    if columns_to_drop != None: all_speed = all_speed.drop(columns=columns_to_drop)
    
    return all_speed

def binSpikes(neurons,binSize = 0.025,start = 0,stop = 0,nbins = None,centered = True):
    '''
        Bin neuronal spikes with difine binSize.
        If no start/stop provided will run trought all the data
        
        If centered will return the center of each bin. Otherwise will return edges
    '''
    
    if stop == 0:
        stop = np.max([neuron.as_units('s').index[-1] for neuron in neurons if any(neuron.index)])
    
    bins = np.arange(start,stop,binSize)
    if nbins: bins = nbins

    binned = np.empty((len(neurons),len(bins)-1),dtype = 'int8')
    

    # IF NUMBER OF BINS IS USED THIS WILL OVERWRITE binSize    
    for i,neuron in enumerate(neurons):
        binned[i],b = np.histogram(neuron.as_units('s').index,bins = bins,range = [start,stop])

    if centered:
        b = np.convolve(b,[.5,.5],'same')[1::]
    return b,binned

def transitions_times(states,epsilon = 1):
    '''
        states : dict of nts.Interval_Set
        
        This function compute transition in between Intervals in a dict.
        It returns a new dict with intervals and when the transition occurs
        
        epsilon : tolerance time delay between state
        
        This function does NOT WORK for triple transitions (ex : sws/rem/sws) ... 
        
    '''
    
    import itertools
    
    empty_state = []
    for state in states:
        if len(states[state]) == 0:
            empty_state.append(state)
            continue
        states[state] = states[state].drop_short_intervals(1)
    
    
    for i in empty_state: del states[i]
        
    transitions_intervals = {}
    transitions_timing = {}
    
    for items in itertools.permutations(states.keys(),2):
#         states[items[0]] = states[items[0]].drop_short_intervals(1)
#         states[items[1]] = states[items[1]].drop_short_intervals(1)
        
        print('Looking at transition from',items[0],' to ',items[1])
        end = nts.Ts(np.array(states[items[0]].end + (epsilon * 1_000_000)+1))
        in_next_epoch = states[items[1]].in_interval(end)
        
        transitions_intervals.update({items:[]})
        transitions_timing.update({items:[]})

        for n,t in enumerate(in_next_epoch):
            if np.isnan(t): continue            
            start = states[items[0]].iloc[n].start
            trans = int(np.mean([states[items[0]].iloc[n].end,states[items[1]].iloc[int(t)].start]))
            end  = states[items[1]].iloc[int(t)].end
            transitions_intervals[items].append([start,end])
            transitions_timing[items].append(trans)
        
        if  not transitions_timing[items] == []:      
            transitions_intervals[items] = np.array(transitions_intervals[items])
            transitions_intervals[items] = nts.IntervalSet(transitions_intervals[items][:,0],transitions_intervals[items][:,1])
            
            transitions_timing[items] = nts.Ts(t = np.array(transitions_timing[items]))
    return transitions_intervals,transitions_timing


def nts_smooth(y,m,std):
    g = scipy.signal.gaussian(m,std)
    g = g/g.sum()
    
    conv = np.convolve(y.values,g,'same')
    
    y = nts.Tsd(y.index.values,conv)
    return y

