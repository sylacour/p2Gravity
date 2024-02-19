#coding: utf8
"""A class inherinting from ObservingBlock to define a dual field off-axis OB in all its glorious specificity
"""

from .. import tpl
from .. import common
from .observingBlock import ObservingBlock

# import re to properly split swap in sequence
import re

import numpy as np

import math

# to resolve planet position
try:
    import whereistheplanet
    WHEREISTHEPLANET = True    
except:
    common.printwar("Cannot load whereistheplanet module. 'whereistheplanet' will not be available as a coord_syst.")
    WHEREISTHEPLANET = False    


class DualOffOb(ObservingBlock):
    def __init__(self, *args, **kwargs):
        """
        See ObservingBlock.__init__
        """        
        super(DualOffOb, self).__init__(*args, **kwargs)
        self.ob_type = "DualOffOb"
        return None

    def _generate_acquisition(self):
        """
        create the acquisition attribute using the appropriate acquisition type and Automatically populate the fields
        the setup dict attribute will also by used to bypass some default values if required
        """        
        self.acquisition = tpl.DualOffAxisAcq()
        self._fill_magnitudes(self.yml)
        # set target names
        if "ft_target" in self.yml:
            self.acquisition["SEQ.FT.ROBJ.NAME"] = self.yml["ft_target"]
        else:
            if not("target" in self.yml):
                printerr("No 'target' specified in ObservingBlocks")
            self.acquisition["SEQ.FT.ROBJ.NAME"] = self.yml["target"]
        if "sc_target" in self.yml:
            self.acquisition["SEQ.INS.SOBJ.NAME"] = self.yml["sc_target"]
        else:
            if not("target" in self.yml):
                printerr("No 'target' specified in ObservingBlocks")                        
            self.acquisition["SEQ.INS.SOBJ.NAME"] = self.yml["target"]
        # use the mean of templates to set the direction of acquisition
        dx = np.array([tpl["SEQ.RELOFF.X"][0] for tpl in self.templates if tpl.template_name == "GRAVITY_dual_obs_exp"]).mean()
        dy = np.array([tpl["SEQ.RELOFF.Y"][0] for tpl in self.templates if tpl.template_name == "GRAVITY_dual_obs_exp"]).mean()
        self.acquisition["SEQ.INS.SOBJ.X"] = round(dx/np.sqrt(dx**2+dy**2), 2) # 1 mas total sep
        self.acquisition["SEQ.INS.SOBJ.Y"] = round(dy/np.sqrt(dx**2+dy**2), 2)                                           
        # last step is to populate with setup, and then star object itself, which can be used to bypass any other setup
        self.acquisition.populate_from_yml(self.setup)
        self.acquisition.populate_from_yml(self.yml)
        if "coord_syst" in self.yml:
            if self.yml["coord_syst"] == "radec":
                self.acquisition["SEQ.INS.SOBJ.X"] = round(self.yml["coord"][0], 2)
                self.acquisition["SEQ.INS.SOBJ.Y"] = round(self.yml["coord"][1], 2)
            elif self.yml["coord_syst"] == "pasep":
                pa, sep = self.yml["coord"]
                ra, dec = math.sin(pa/180*math.pi)*sep, math.cos(pa/180.0*math.pi)*sep
                self.acquisition["SEQ.INS.SOBJ.X"] = round(ra, 2)
                self.acquisition["SEQ.INS.SOBJ.Y"] = round(dec, 2)
            elif self.yml["coord_syst"] == "whereistheplanet":
                if WHEREISTHEPLANET:
                    common.printinf("Resolution of {} with whereistheplanet:".format(self.yml["coord"]))
                    ra, dec, sep, pa = whereistheplanet.predict_planet(self.yml["coord"], self.setup["date"])
                    self.acquisition["SEQ.INS.SOBJ.X"] = round(ra[0], 2)
                    self.acquisition["SEQ.INS.SOBJ.Y"] = round(dec[0], 2)                  
                else: 
                    common.printerr("whereistheplanet used as a coord_syst, but whereistheplanet module could not be loaded")
            else:
                common.printerr("Unknown coordinate system {}".format(self.yml["coord_syst"]))
        return None

    def _generate_template(self, exposures):
        """
        generate the template from the given yml dict and exposure 
        """        
        if exposures == "swap":
            template = tpl.DualObsSwap()            
            template.populate_from_yml(self.yml)
        else:
            template = tpl.DualObsExp(iscalib = self.iscalib)            
            template["SEQ.RELOFF.X"] = []
            template["SEQ.RELOFF.Y"] = []            
            exposures_ESO = ""                
            for exposure in exposures:
                if exposure.lower() == "sky":
                    template["SEQ.RELOFF.X"].append(0.)
                    template["SEQ.RELOFF.Y"].append(0.)
                    exposures_ESO = exposures_ESO + " S"
                else:
                    if not(exposure  in self.objects):
                        printerr("Object with label {} from sequence not found in yml".format(exposure))
                    obj_yml = self.objects[exposure]
                    if "coord_syst" in obj_yml:
                        if obj_yml["coord_syst"] == "radec":
                            template["SEQ.RELOFF.X"].append(round(obj_yml["coord"][0], 2))
                            template["SEQ.RELOFF.Y"].append(round(obj_yml["coord"][1], 2))                          
                        elif obj_yml["coord_syst"] == "pasep":
                            pa, sep = obj_yml["coord"]
                            ra, dec = math.sin(pa/180*math.pi)*sep, math.cos(pa/180.0*math.pi)*sep
                            template["SEQ.RELOFF.X"].append(round(obj_yml["coord"][0], 2))
                            template["SEQ.RELOFF.Y"].append(round(obj_yml["coord"][1], 2))
                        elif obj_yml["coord_syst"] == "whereistheplanet":
                            if WHEREISTHEPLANET:
                                common.printinf("Resolution of {} with whereistheplanet:".format(obj_yml["coord"]))
                                ra, dec, sep, pa = whereistheplanet.predict_planet(obj_yml["coord"], self.setup["date"])
                                template["SEQ.RELOFF.X"].append(round(obj_yml["coord"][0], 2))
                                template["SEQ.RELOFF.Y"].append(round(obj_yml["coord"][1], 2))                                                                   
                            else: 
                                common.printerr("whereistheplanet used as a coord_syst, but whereistheplanet module could not be loaded")
                        else:
                            common.printerr("Unknown coordinate system {}".format(obj_yml["coord_syst"]))
                    else:
                        template["SEQ.RELOFF.X"].append(0.)
                        template["SEQ.RELOFF.Y"].append(0.)                            
                    # add the exposure in the ESO format
                    exposures_ESO = exposures_ESO + " O"
                    # don't forget that these offsets are cumulative, so we need to
                    # remove the previous cumsum from each newly calculated offset
                    template["SEQ.RELOFF.X"][-1] = template["SEQ.RELOFF.X"][-1] - np.sum(np.array(template["SEQ.RELOFF.X"][:-1]))
                    template["SEQ.RELOFF.Y"][-1] = template["SEQ.RELOFF.Y"][-1] - np.sum(np.array(template["SEQ.RELOFF.Y"][:-1]))            
                    template.populate_from_yml(obj_yml)
            template["SEQ.OBSSEQ"] = exposures_ESO            
        return template

    def generate_templates(self):
        """
        generate the sequence of templates corresponding to the OB. Nothing is send to P2 at this point
        """
        # split sequences on swaps:
        sequences = []
        for seq in self.yml["sequence"]:
            for dummy in re.split("(\W|\A)(swap)", seq.rstrip().lstrip()):
                dummy = dummy.rstrip().lstrip()
                if dummy != "":
                    sequences.append(dummy)
        for seq in sequences:
            exposures = seq.rstrip().lstrip().split(" ")
            if exposures == ["swap"]: # no test in this case
                self.templates.append(self._generate_template("swap"))
            else:
                if len(set([dummy for dummy in exposures if dummy != "sky"])) > 1: # more than one object which is not sky
                    if len(set([self.objects[dummy]["DET2.DIT"] for dummy in exposures if dummy != "sky"])) > 1 : # check if all dits are the same
                        common.printerr("Sequence '{}' in OB '{}' contains objects with different DET2.DIT. Please split them on different lines.".format(exposures, self.label))
                    if len(set([self.objects[dummy]["DET2.NDIT.SKY"] for dummy in exposures if dummy != "sky"])) > 1 : # check if all dits are the same
                        common.printerr("Sequence '{}' in OB '{}' contains objects with different DET2.NDIT.SKY.. Please split them on different lines.".format(exposures, self.label))
                    if len(set([self.objects[dummy]["DET2.NDIT.OBJECT"] for dummy in exposures if dummy != "sky"])) > 1 : # check if all dits are the same
                        common.printerr("Sequence '{}' in OB '{}' contains objects with different DET2.NDIT.OBJECT. Please split them on different lines.".format(exposures, self.label))
                if not("sky" in exposures):
                    common.printwar("No sky in sequence {} in OB '{}'".format(exposures, self.label))
                self.templates.append(self._generate_template(exposures))
        # now we can generate acquisition                
        self._generate_acquisition()
        return None
            

