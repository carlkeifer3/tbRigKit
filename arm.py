import maya.cmds as cmds
import maya.OpenMaya as OpenMaya
import utils as utils

class Skeleton(object):
    """
    Skeleton Base Class
    """
    def __init__(self):
        self.utils = utils()
        self.prefix = 'l_'
        self.suffix = 'fk'
        self.shoulder = ('%sshoulder%s' % (self.prefix, self.suffix))
        self.elbow = ('%selbow_%s' % (self.prefix, self.suffix))
        self.wrist = ('%swrist_%s' % (self.prefix, self.suffix))
        self.radius = 0.2
        self.scale = 1


class FKSkeleton(Skeleton):
    """
    FK Skeleton Class: Extends Skeleton
    """
    def __init__(self):
        super(FKSkeleton, self).__init__()

    def createFkControls(self, controlJoints=[], skinJoints=[]):
        controls = []
        nullGroups = []
        index = 0

        print "Building FK Controls..."
        # Create a circle control at each joint
        for controlJoint, skinJoint in zip(controlJoints, skinJoints):
            control = self.utils.createCircleControl(skinJoint.replace('_bind', 'CON'), 0.5)
            self.utils.parentSnap(skinJoint, control[0])
            cmds.orientConstraint(control[0], controlJoint)
            nullGroup = self.utils.createNullGroup(control[0])
            self.utils.lockAttrs(control[0], 1, 0, 1, 1)
            controls.append(control[0])
            nullGroups.append(nullGroup)

        for index in range(index, len(controls) - 1):
            cmds.parent(nullGroups[index + 1], controls[index])


class IKSkeleton(Skeleton):
    """
    IK Skeleton Class: Extends Skeleton
    """
    def __init__(self):
        super(IKSkeleton, self).__init__()
        self.suffix = 'ik'
        self.shoulder = ('%sshoulder_%s' % (self.prefix, self.suffix))
        self.elbow = ('%selbow_%s' % (self.prefix, self.suffix))
        self.wrist = ('%swrist_%s' % (self.prefix, self.suffix))

    def createIkHandle(self):
        print 'Building ik handle...'
        ikHandle = cmds.ikHandle(n=self.wrist.replace('wrist_ik', 'armHDL'),
                                 startJoint=self.shoulder, endEffector=self.wrist, solver='ikRPsolver')
        return ikHandle

    def createWristControl(self):
        print 'Building wrist control...'
        wristControl = self.utils.createBoxControl('%shandCON' % self.prefix, 0.25)
        self.utils.parentSnap(self.wrist, wristControl)
        return wristControl

    def createPoleVector(self, prefix=None, distanceScale=2, verbose=False):
        print 'Building pole vector...'

        if prefix is None:
            prefix = self.prefix

        # Create Joint Vectors
        shoulderIkPos = cmds.xform(self.shoulder, q=True, ws=True, t=True)
        shoulderIkVec = OpenMaya.MVector(shoulderIkPos[0], shoulderIkPos[1], shoulderIkPos[2])
        elbowIkPos = cmds.xform(self.elbow, q=True, ws=True, t=True)
        elbowIkVec = OpenMaya.MVector(elbowIkPos[0], elbowIkPos[1], elbowIkPos[2])
        wristIkPos = cmds.xform(self.wrist, q=True, ws=True, t=True)
        wristIkVec = OpenMaya.MVector(wristIkPos[0], wristIkPos[1], wristIkPos[2])

        # Transpose vectors to correct pole vector translation point
        bisectorVec = (shoulderIkVec * 0.5) + (wristIkVec * 0.5)
        transposedVec = (elbowIkVec * distanceScale) - (bisectorVec * distanceScale)
        ikChainPoleVec = bisectorVec + transposedVec

        # Create a pole vector
        poleVecCon = self.utils.createBoxControl('%selbowPV' % self.prefix, 0.125)
        poleVecPos = [ikChainPoleVec.x, ikChainPoleVec.y, ikChainPoleVec.z]
        cmds.xform(poleVecCon, t=poleVecPos)
        self.utils.orientSnap(self.elbow, poleVecCon)

        # Visualize Vectors and End Points
        if verbose:
            for vector, letter in zip([bisectorVec, transposedVec, ikChainPoleVec,
                                       shoulderIkVec, elbowIkVec, wristIkVec],
                                      ['bisectorVec', 'transposedVec', 'ikChainPoleVec',
                                      'shoulderIk', 'elbowIk', 'wristIk']):
                cmds.spaceLocator(n='%sVecLoc' % letter, p=[vector.x, vector.y, vector.z])
                cmds.curve(n='%sVecCurve' % letter, degree=1, p=[(0, 0, 0), (vector.x, vector.y, vector.z)])

        return poleVecCon

    def createIkControls(self):
        # Create controls and solvers
        wristControl = self.createWristControl()
        poleVector = self.createPoleVector(distanceScale=5)
        ikHandle = self.createIkHandle()[0]

        # Create and constrain arm ik handle
        cmds.pointConstraint(wristControl, ikHandle)
        cmds.poleVectorConstraint(poleVector, ikHandle)

        # Create null groups
        self.utils.createNullGroup(wristControl)
        self.utils.createNullGroup(poleVector)

        # Lock controller attributes
        self.utils.lockAttrs(wristControl, rotate=True, scale=True, visibility=True)
        self.utils.lockAttrs(poleVector, rotate=True, scale=True, visibility=True)

# Create an Arm Rig
myUtils = utils()
myIkArm = IKSkeleton()
myFkArm = FKSkeleton()
prefix = 'l_'
armBindJoints = ['%sshoulder_bind' % prefix, '%selbow_bind' % prefix, '%swrist_bind' % prefix]

# Create IK Armutils
myUtils.jointCheck(armBindJoints)
ikJoints = myUtils.createJoints(armBindJoints, myIkArm.prefix, myIkArm.suffix, myIkArm.radius)
myIkArm.createIkControls()

# Create Fk Arm
fkJoints = myUtils.createJoints(armBindJoints, myFkArm.prefix, myFkArm.suffix, myFkArm.radius)
myFkArm.createFkControls(fkJoints, armBindJoints)

# Position IK/FK Switcher
switcherCon = myUtils.createStarControl('%sArmSwitcher' % prefix)
myUtils.parentSnap(myFkArm.wrist, switcherCon)
cmds.move(0, 1, 0, switcherCon, r=1, os=1)
myUtils.clearSel()

# Add and Connect Switcher Attributes
cmds.parentConstraint(armBindJoints[-1], switcherCon[0], mo=1)
myUtils.lockAttrs(switcherCon[0], 1, 1, 1, 1)
cmds.addAttr(switcherCon[0], longName='switcher', attributeType='enum', enumName='IK:FK', keyable=True)

# Constrain Bind Joints to Control Joints
reverser = cmds.createNode('reverse', n='%sSwitcherReverse' % prefix)
cmds.connectAttr('%s.switcher' % switcherCon[0], '%s.inputX' % reverser)

for bindJoint, ikJoint, fkJoint in zip(armBindJoints, ikJoints, fkJoints):
    orient = myUtils.orientConstraint([ikJoint, fkJoint], bindJoint)
    point = myUtils.pointConstraint([ikJoint, fkJoint], bindJoint)
    cmds.connectAttr('%s.switcher' % switcherCon[0], '%s.%s' % (orient[0], bindJoint.replace('bind', 'fkW1')))
    cmds.connectAttr('%s.outputX' % reverser, '%s.%s' % (orient[0], bindJoint.replace('bind', 'ikW0')))
    cmds.connectAttr('%s.switcher' % switcherCon[0], '%s.%s' % (point[0], bindJoint.replace('bind', 'fkW1')))
    cmds.connectAttr('%s.outputX' % reverser, '%s.%s' % (point[0], bindJoint.replace('bind', 'ikW0')))