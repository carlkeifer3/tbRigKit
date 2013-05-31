import maya.cmds as cmds


class Utilities(object):
    """
    General Maya command utilities
    """
    def sel(self):
        return cmds.ls(sl=True, fl=True)

    def delete(self, object):
        if cmds.objExists(object):
            cmds.delete(object)

    def clearSel(self):
        cmds.select(clear=True)

    def parentSnap(self, source, target):
        cmds.delete(cmds.parentConstraint(source, target))

    def pointSnap(self, source, target):
        cmds.delete(cmds.pointConstraint(source, target))

    def orientSnap(self, source, target):
        cmds.delete(cmds.orientConstraint(source, target))

    def parentConstraint(self, source, target):
        try:
            constraint = cmds.parentConstraint(source, target)
            return constraint
        except:
            cmds.error('Could not constrain')

    def pointConstraint(self, source, target):
        try:
            constraint = cmds.pointConstraint(source, target)
            return constraint
        except:
            cmds.error('Could not constrain')

    def orientConstraint(self, source, target):
        try:
            constraint = cmds.orientConstraint(source, target)
            return constraint
        except:
            cmds.error('Could not constrain')

    def createNullGroup(self, source, name=None):
        xyz = ['X', 'Y', 'Z']
        if name is None:
            if 'CON' in source:
                name = ('%sNUL' % source.replace('CON', ''))
            else:
                name = ('%sNUL' % source)
        group = cmds.group(em=True, name=name)
        trans = cmds.xform(source, q=True, ws=True, t=True)
        rots = cmds.xform(source, q=True, ws=True, ro=True)
        sourceParent = cmds.listRelatives(source, p=True)

        for index, item in enumerate(xyz):
            cmds.setAttr(('%s.translate%s' % (group, item)), trans[index])
            cmds.setAttr(('%s.rotate%s' % (group, item)), rots[index])

        cmds.parent(source, group)
        if sourceParent is not None:
            cmds.parent(group, sourceParent)

        return group

    def lockAttrs(self, source, translate=False, rotate=False, scale=False, visibility=False):
        for axis in ['X', 'Y', 'Z']:
            if translate:
                cmds.setAttr('%s.%s%s' % (source, 'translate', axis), keyable=False, lock=True, channelBox=False)
            if rotate:
                cmds.setAttr('%s.%s%s' % (source, 'rotate', axis), keyable=False, lock=True, channelBox=False)
            if scale:
                cmds.setAttr('%s.%s%s' % (source, 'scale', axis), keyable=False, lock=True, channelBox=False)
        if visibility:
            cmds.setAttr('%s.%s' % (source, 'visibility'), keyable=False, lock=True, channelBox=False)

    def jointCheck(self, jointCheckList=[]):
        for joint in jointCheckList:
            if cmds.objExists(joint):
                continue
            else:
                cmds.error('Could not find joint: %s, please check joint names' % joint)
                break
        print '\\nFound all bind joints...'

    def createJoints(self, jointPositions=[], prefix='', suffix='', radius=1):
        print 'Building skeleton joints...'
        self.clearSel()
        myJoints = []
        for joint in jointPositions:
            jointOrients = cmds.getAttr('%s.jointOrient' % joint)
            myJointName = joint.replace('bind', suffix).replace('l_', prefix) or joint.replace('r_', prefix)
            myJoint = cmds.joint(n=myJointName, radius=radius, orientation=jointOrients[0])
            self.parentSnap(joint, myJoint)
            myJoints.append(myJoint)
        return myJoints

    def createBoxControl(self, name='', scale=1):
        curveShape = [(scale, -scale, scale), (scale, scale, scale), (scale, scale, -scale), (scale, -scale, -scale),
                      (-scale, -scale, -scale), (-scale, scale, -scale), (-scale, scale, scale), (-scale, -scale, scale),
                      (scale, -scale, scale), (scale, -scale, -scale), (-scale, -scale, -scale), (-scale, -scale, scale),
                      (-scale, scale, scale), (scale, scale, scale), (scale, scale, -scale), (-scale, scale, -scale)]
        boxControl = cmds.curve(name=name, d=1, p=curveShape)
        return boxControl

    def createCircleControl(self, name='', radius=1, sections=8):
        circleControl = cmds.circle(name=name, radius=radius, sections=sections)
        return circleControl

    def createStarControl(self, name='', radius=0.5, sections=16, parentSpace=None):
        self.clearSel()
        starControl = self.createCircleControl(name, radius, sections)
        cvs = [cvs for cvs in range(1, sections) if cvs % 2 != 0]
        for cv in cvs:
            cmds.select('%s.cv[%d]' % (starControl[0], cv), add=1)
            cmds.scale(.1, .1, .1, '%s.cv[%d]' % (starControl[0], cv), r=1)
        return starControl
