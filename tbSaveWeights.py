# ---- Save python file to plugin directory ----
# ---- Re-Open Maya ----
# import maya.cmds as cmds
# import maya.mel as mel
# cmds.unloadPlugin('tbSaveWeights.py')
# cmds.loadPlugin('tbSaveWeights.py')

# ---- Export Weights ----
# ---- Select Mesh ----
# mel.eval('tbSaveSkinWeights -a "export" -f "c:/weights.xml"')

# ---- Import Weights ----
# ---- Select Mesh ----
# mel.eval('tbSaveSkinWeights -a "import" -f "c:/weights.xml"')

# Code Resources: Nicholas Bolden, Tyler Thornock
# TO DO: Add boiler plate

import sys
import time
import xml.etree.cElementTree as cElement

import maya.OpenMaya as om
import maya.OpenMayaMPx as ompx
import maya.OpenMayaAnim as oma
import maya.cmds as cmds
import maya.mel as mel

# Param Flags
kTbSaveWeightsFileParam = 'file'
kTbSaveWeightsActionParam = 'action'
kTbSaveWeightsRoundOffParam = 'roundOff'

# Command Flags
kPluginCmdName = 'tbSaveSkinWeights'
kTbSaveWeightsFileFlag = '-f'
kTbSaveWeightsFileLongFlag = '-File'
kTbSaveWeightsActionFlag = "-a"
kTbSaveWeightsActionLongFlag = "-Action"

class tbSaveSkinWeights(ompx.MPxCommand):
    def __init__(self):
        ompx.MPxCommand.__init__(self)

        self.defaultFileName = 'c:/weights.xml'
        self.maxInfluences = 4
        self.minWeight = 0
        self.maxWeight = 1
        self.skinCluster = 'skinCluster1'
        self.weights = {}

    def doIt(self, argList):
        argData = om.MArgDatabase(self.syntax(), argList)

        # Check our flags
        fileFlagSet = argData.isFlagSet(kTbSaveWeightsFileFlag)
        actionFlagSet = argData.isFlagSet(kTbSaveWeightsActionFlag)

        if fileFlagSet:
            self.fileName = argData.flagArgumentString(kTbSaveWeightsFileFlag, 0)
        else:
            self.fileName = self.defaultFileName

        if actionFlagSet:
            self._action = argData.flagArgumentString(kTbSaveWeightsActionFlag, 0)

        self.main()

    def main(self):
        print 'Running main...'

        if self._action == 'export':
            print 'Exporting weights...'
            self.skinCluster = self.getSkinCluster()
            self.infDags = self.getInfDags(self.skinCluster)
            self.weights = self.saveWeights(self.infDags, self.skinCluster)
            self.exportWeights(self.weights, self.fileName)

        elif self._action == 'import':
            print 'Importing weights...'
            startTime = time.time()
            self.selName = self.getSelString()
            self.skinCluster = self.getSkinCluster()
            self.infDags = self.getInfDags(self.skinCluster)
            self.infNames = self.getInfNames(self.infDags, self.skinCluster)
            self.weights = self.importWeights()
            self.normalizeWeights(self.selName, self.infNames, self.skinCluster)
            self.setWeights(self.skinCluster, self.weights)
            endTime = time.time()
            print('Import weights took %g seconds' % (endTime - startTime))

        return

    def setWeights(self, clusterNode, weights):
        """
        Using a weight dictionary, set the object weights:
        Parse through the weight dictionary and use setAttr to set weights
        setAttr is a faster method than MFnSkinCluster.setWeights()
        setAttr gives free undo capabilities
        """
        # Check for a weight dictionary
        if not type(weights) is dict:
            raise Exception("Weights dict not found")
            return False

        clusterName = clusterNode.name()

        # Loop through the weights dictionary
        for vertId, weightData in weights.items():
            wlAttr = '%s.weightList[%s]' % (clusterName, vertId)

            for infId, infValue in weightData.items():
                wAttr = '.weights[%s]' % infId

                # TODO: Check to make sure influence object weights add to 1
                a = [float(i) for i in weightData.values()]
                infValueSumCheck = round(sum(a), 2)
                b = self.infNames[int(infId)] + '.worldMatrix[0]'
                c = clusterName + '.matrix[%d]' % int(infId)
                # Check to make sure influence objects are connected to mesh
                isConnectedCheck = cmds.isConnected(b, c)

                if infValueSumCheck and isConnectedCheck:
                    # PRIMARY METHOD - VERY FAST
                    cmds.setAttr(wlAttr + wAttr, float(infValue))
                else:
                    # ALT METHOD - VERY SLOW
                    cmds.skinPercent(clusterName, '%s.vtx[%d]' % (self.selName, int(vertId)),
                                     transformValue=[(self.infNames[int(infId)], float(infValue))])

        return True

    def normalizeWeights(self, selName, infNames, clusterNode):
        """
        Remove non-zero weighting:
        Temporarily removing weight normalization allows for a weight prune
        Weight pruning is done to remove all non-zero weighting
        Non-zero weighting is removed to compress object data (faster speed) and file size
        """
        clusterName = clusterNode.name()

        # Unlock influences first
        for inf in infNames:
            cmds.setAttr('%s.liw' % inf, 0)

        # Temporarily turn off normalize
        normalizeSetting = cmds.getAttr('%s.normalizeWeights' % clusterName)

        if normalizeSetting != 0:
            cmds.setAttr('%s.normalizeWeights' % clusterName, 0)

        # Prune non-zero weights
        cmds.skinPercent(clusterName, selName, nrm=False, prw=100)
        # Turn normalize back on
        if normalizeSetting != 0:
            # cmds.setAttr('%s.normalizeWeights' % clusterName, normalizeSetting)
            cmds.setAttr('%s.normalizeWeights' % clusterName, normalizeSetting)

    def getSkinCluster(self):
        """
        Get a selected object's skin cluster as a MFnSkinCluster
        """
        # Store selection in MSelectionList
        sel = om.MSelectionList()
        om.MGlobal.getActiveSelectionList(sel)

        # Check only one object selected
        if not sel.length() == 1:
            raise Exception("Select only one object")

        # Find mesh's related skin cluster
        selObjs = []
        sel.getSelectionStrings(selObjs)
        self.selName = selObjs[0]
        clusterNode = mel.eval('findRelatedSkinCluster %s' % self.selName)
        sel.add(clusterNode)
        clusterObj = om.MObject()
        sel.getDependNode(1, clusterObj)
        skinFn = oma.MFnSkinCluster(clusterObj)
        return skinFn

    def getSelString(self):
        """
        Get Selected object as a selectionString to be passed around methods
        """
        sel = om.MSelectionList()
        om.MGlobal.getActiveSelectionList(sel)
        selObjs = []
        sel.getSelectionStrings(selObjs)
        return selObjs[0]

    def getInfDags(self, skinFn):
        """
        Get influence dag objects to be passed around methods
        """
        infDags = om.MDagPathArray()
        skinFn.influenceObjects(infDags)
        return infDags

    def getInfNames(self, infDags, skinFn):
        """
        Get a list of influence names
        Influence names are used to iterate through and normalize weights
        See normalizeWeights()
        """
        infNames = [infDags[i].partialPathName() for i in xrange(infDags.length())]
        return infNames

    def saveWeights(self, infDags, skinFn):
        """
        Uses a dictionary to save mesh weights:
        """
        # infIds dictionary:
        # keys = MPlug index id
        # values = influence list id
        infIds = {}
        infs = []
        for i in xrange(infDags.length()):
            infPath = infDags[i].fullPathName()
            infId = int(skinFn.indexForInfluenceObject(infDags[i]))
            infIds[infId] = i
            infs.append(infPath)

        # get the MPlug for the weightList and weights attributes
        wlPlug = skinFn.findPlug('weightList')
        wPlug = skinFn.findPlug('weights')
        wlAttr = wlPlug.attribute()
        wAttr = wPlug.attribute()
        wInfIds = om.MIntArray()

        # weights dictionary:
        # weights keys = vertex id
        # weights values = a vertex weights dictionary:
        # vWeights keys = influence id
        # vWeights values = influence weight (value)
        weights = {}
        for vId in xrange(wlPlug.numElements()):
            vWeights = {}
            wPlug.selectAncestorLogicalIndex(vId, wlAttr)
            wPlug.getExistingArrayAttributeIndices(wInfIds)
            infPlug = om.MPlug(wPlug)

            for infId in wInfIds:
                infPlug.selectAncestorLogicalIndex(infId, wAttr)

                try:
                    vWeights[infIds[infId]] = infPlug.asDouble()
                except KeyError:
                    pass
            weights[vId] = vWeights

        return weights

    def importWeights(self, weights={}):
        """
        Open the file
        Create a weights dictionary
        """
        startTime = time.time()
        tree = cElement.parse(self.fileName)
        root = tree.getroot()
        mesh = root.find('mesh')

        if mesh.attrib.get('name') != self.selName:
            raise Exception('Selected mesh does not match weights file mesh')

        for vertId in mesh:
            # print vertId.tag, vertId.attrib
            index = vertId.get('index')
            # print 'index:', index
            weights[index] = {}
            for inf in vertId:
                attribs = {inf.get('idx'): inf.get('weight')}
                # print attribs
                weights[index].update(attribs)

        endTime = time.time()
        print('Read time was %g seconds' % (endTime - startTime))
        return weights

    def exportWeights(self, weights={}, fileName=None, printPretty=True):
        """
        Generate an XML document
        """
        # TO DO: Add pretty print option flag - will build this into qt widget ui
        
        startTime = time.time()

        # Write to XML using cElementTree
        root = cElement.Element("root")
        mesh = cElement.SubElement(root, 'mesh', {'name': self.selName})

        for (vertId, subWeights) in weights.iteritems():
            vertIdElem = cElement.SubElement(
                mesh, 'vertId', {'index': str(vertId), 'path': '%s.vtx[%s]' % (self.selName, str(vertId))})
            for (infIndex, infWeight) in subWeights.iteritems():
                cElement.SubElement(vertIdElem, 'inf', {'idx': str(infIndex), 'weight': str(infWeight)})

        endComment = cElement.Comment('eof')
        root.append(endComment)

        if not fileName:
            fileName = self.defaultFileName

        f = open(fileName, 'w')

        if printPretty:
            f.write(self.prettify(root))
        else:
            cElement.ElementTree(root).write(f)

        f.close()

        endTime = time.time()
        print("Export weights took %g seconds" % (endTime - startTime))

    def prettify(self, elem):
        """Return a pretty-printed XML string for the Element.
        """
        from xml.etree import ElementTree
        from xml.dom import minidom

        rough_string = ElementTree.tostring(elem, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")


#--------------------------------------------------#
#--------------------------------------------------#
#--------------------------------------------------#
#--------         Command Methods       -----------#
#--------------------------------------------------#
#--------------------------------------------------#
#--------------------------------------------------#
def cmdCreator():
    """
    Command Creator
    """
    return ompx.asMPxPtr(tbSaveSkinWeights())


def syntaxCreator():
    """
    Syntax Creator
    """
    syntax = om.MSyntax()
    syntax.addFlag(kTbSaveWeightsFileFlag, kTbSaveWeightsFileLongFlag, om.MSyntax.kString)
    syntax.addFlag(kTbSaveWeightsActionFlag, kTbSaveWeightsActionLongFlag, om.MSyntax.kString)
    return syntax


def initializePlugin(mobject):
    """ Load the command and register defined classes """
    mplugin = ompx.MFnPlugin(mobject, 'Tom Banker', '1.1', 'Any')
    try:
        mplugin.registerCommand(kPluginCmdName, cmdCreator, syntaxCreator)
    except Exception, e:
        sys.stderr.write('Failed to register command: %s\n" % kPluginCmdName')
        sys.stderr.write('%s\n' % e)


def uninitializePlugin(mobject):
    """ Unload the command and unregister defined classes """
    mplugin = ompx.MFnPlugin(mobject)
    try:
        mplugin.deregisterCommand(kPluginCmdName)
    except:
        sys.stderr.write('Failed to unregister command: %s\n' % kPluginCmdName)
