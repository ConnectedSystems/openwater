'''
Configuration node-link network catchment models for Openwater.

Includes:

* Support for delineation based on a DEM, using TauDEM
* Spatial parameterisation (python-rasterstats)
* Spatial input generation using climate-utils
'''
from openwater import OWTemplate, OWLink
import openwater.nodes as n


# Need:
# * Routines for delineation
# * 

class SemiLumpedCatchment(object):
  def __init__(self):
    self.hrus = ['HRU']
    self.cgus = ['CGU']
    self.cgu_hrus = {'CGU':'HRU'}
    self.constituents = ['Con']

    self.rr = n.Simhyd
    self.cg = n.EmcDwc
    self.routing = n.Muskingum
    self.transport = n.LumpedConstituentRouting

  def model_for(self,provider,*args):
    if hasattr(provider,'__call__'):
      return provider(*args)
    if hasattr(provider,'__getitem__'):
      return provider[args[0]]
    return provider

  def get_template(self):
    template = OWTemplate()

    routing_node = template.add_node(self.routing,process='FlowRouting')
    transport = {}
    for con in self.constituents:
        # transport_node = 'Transport-%s'%(con)
        transport_node = template.add_node(self.model_for(self.transport,con),process='ConstituentRouting',constituent=con)
        template.add_link(OWLink(routing_node,'outflow',transport_node,'outflow'))
        transport[con]=transport_node

    for hru in self.hrus:
        runoff_node = template.add_node(self.model_for(self.rr,hru),process='RR',hru=hru)
        runoff_scale_node = template.add_node(n.DepthToRate,process='ArealScale',hru=hru,component='Runoff')
        quickflow_scale_node = template.add_node(n.DepthToRate,process='ArealScale',hru=hru,component='Quickflow')
        baseflow_scale_node = template.add_node(n.DepthToRate,process='ArealScale',hru=hru,component='Baseflow')

        template.add_link(OWLink(runoff_node,'runoff',runoff_scale_node,'input'))      
        template.add_link(OWLink(runoff_node,'quickflow',quickflow_scale_node,'input'))      
        template.add_link(OWLink(runoff_node,'baseflow',baseflow_scale_node,'input'))      

        template.add_link(OWLink(runoff_scale_node,'outflow',routing_node,'lateral'))

        for con in self.constituents:
            # transport_node = 'Transport-%s'%(con)
            transport_node = transport[con]
            template.add_link(OWLink(runoff_scale_node,'outflow',transport_node,'inflow'))
            for cgu in [cgu for cgu,h in self.cgu_hrus.items() if h==hru]:
                #gen_node = 'Generation-%s-%s'%(con,lu)
                gen_node = template.add_node(self.model_for(self.cg,con,cgu),process='ConstituentGeneration',constituent=con,lu=cgu)
                template.add_link(OWLink(quickflow_scale_node,'outflow',gen_node,'quickflow'))
                template.add_link(OWLink(baseflow_scale_node,'outflow',gen_node,'baseflow'))
                template.add_link(OWLink(gen_node,'totalLoad',transport_node,'lateralLoad'))

    return template
  
  def link_catchments(self,graph,upstream,downstream):
    linkages = [('%d-FlowRouting ('+self.routing.name+')','outflow','inflow')] + \
               [(('%%d-ConstituentRouting-%s ('+self.transport.name+')')%c,'outflowLoad','inflowLoad') for c in self.constituents]
    for (lt,src,dest) in linkages:
        dest_node = lt%upstream
        src_node = lt%downstream#'%d/%s'%(to_cat,lt)
        graph.add_edge(src_node,dest_node,src=[src],dest=[dest])

