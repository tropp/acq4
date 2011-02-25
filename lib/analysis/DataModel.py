# -*- coding: utf-8 -*-
import DataManager

getDataModel(obj):
    """Return a data model object constructed from the input."""
    model = None
    if isinstance(obj, DataManager.FileHandle):
        
        
    if model is None:
        raise Exception("Could not generate model for object %s" % str(obj))

    return model





class DataModel:
    """Class for formalizing the raw data structures used in analysis.
    Should allow simple questions like
        Were any scan protocols run under this cell?
        Is this a sequence protocol or a single?
        Give me a meta-array linking all of the data in a sequence (will have to use hdf5 for this?)
        Give me a meta-array of all images from 'Camera' in a sequence (will have to use hdf5 for this?)
        
        Give me the clamp device for this protocol run
        tell me the temperature of this run
        tell me the holding potential for this clamp data
        possibly DB integration?
        
    Notes:
        Shpuld be able to easily switch to a different data model
        Objects may have multiple types (ie protocol seq and photostim scan)
        An instance of this class refers to any piece of data, but most commonly will refer to a directory or file.
        
    """
    def __init__(self, dataTypes):
        self.dataTypes = dataTypes
    
    




class Day(DataModel):
    pass

class Slice(DataModel):
    pass

class Cell(DataModel):
    pass

class Protocol(DataModel):
    pass

class ProtocolSequence(Protocol):
    pass

class ProtocolRun(DataModel):
    pass


