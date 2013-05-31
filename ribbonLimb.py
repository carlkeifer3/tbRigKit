import maya.cmds as cmds
import maya.mel as mel

cmds.select(all=1)
cmds.delete()


def flexiPlaneSetup(prefix='flexiPlane', numJoints=5):
    width = numJoints * 2

    # Create Nurbs surface
    flexiPlane = cmds.nurbsPlane(w=width, lr=0.1,
                                 u=width / 2, v=1, ax=[0, 1, 0])

    flexiPlane = cmds.rename(flexiPlane[0], '%s_surface01' % prefix)
    cmds.delete(flexiPlane, constructionHistory=1)

    # Create plane follicles
    mel.eval('createHair %s 1 2 0 0 0 0 1 0 1 1 1;' % str(width / 2))
    for obj in ['hairSystem1', 'pfxHair1', 'nucleus1']:
        cmds.delete(obj)
    folChildren = cmds.listRelatives('hairSystem1Follicles', ad=1)
    cmds.delete([i for i in folChildren if 'curve' in i])
    folGrp = cmds.rename('hairSystem1Follicles', '%s_flcs01' % prefix)

    alphabetList = map(chr, range(97, 123))
    folChildren = cmds.listRelatives(str(folGrp), c=1)

    for obj, letter in zip(folChildren, alphabetList):
        folJnt = cmds.joint(p=cmds.xform(obj, t=1, q=1), n='%s_bind_%s01' % (prefix, letter))
        cmds.parent(folJnt, obj)
        cmds.rename(obj, '%s_flc_%s01' % (prefix, letter))

    # Add controls
    squareCons = ['%s_cnt_a01' % prefix, '%s_cnt_b01' % prefix, '%s_midBend01' % prefix]

    for squareCon in squareCons:
        squareCon = cmds.curve(n=squareCon, d=1, p=[(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1), (-1, 0, -1)])
        cmds.scale(.75, .75, .75, squareCon, r=1)
        cmds.setAttr('%s.overrideEnabled' % squareCon, 1)
        cmds.setAttr('%s.overrideColor' % squareCon, 17)
        cmds.xform(squareCon, roo='xzy')

    cmds.xform(squareCons[0], t=(-width / 2, 0, 0), ws=1)
    cmds.xform(squareCons[1], t=(width / 2, 0, 0), ws=1)
    cmds.xform(squareCons[2], t=(0, 0, 0), ws=1)
    cmds.makeIdentity(squareCons, a=1)

    squareConGrp = cmds.group(squareCons[0], squareCons[1], n='%s_cnts01' % prefix)
    midConGrp = cmds.group(squareCons[2], n='%s_midCnt01' % prefix)
    cmds.parent(midConGrp, squareConGrp)
    cmds.pointConstraint(squareCons[1], squareCons[0], midConGrp, mo=0)

    # Create a target blendshape controlled by deformers
    flexiBlend = cmds.duplicate(flexiPlane, n='flexiPlaneSetup_bShp_surface01')
    flexiBlendNode = cmds.blendShape(flexiBlend, flexiPlane, n='%s_bShpNode_surface01' % prefix)
    cmds.setAttr('%s.%s' % (flexiBlendNode[0], flexiBlend[0]), 1)
    wireCurve = cmds.curve(n='%s_wire_surface01' % prefix, d=2, p=[(-width / 2, 0, 0), (0, 0, 0), (width / 2, 0, 0)])
    topClstr = cmds.cluster('%s.cv[0:1]' % wireCurve, rel=1, n='%s_cl_a01' % prefix)
    midClstr = cmds.cluster('%s.cv[1]' % wireCurve, rel=1, n='%s_cl_mid01' % prefix)
    botClstr = cmds.cluster('%s.cv[1:2]' % wireCurve, rel=1, n='%s_cl_b01' % prefix)
    clsGrp = cmds.group(topClstr, midClstr, botClstr, n='%s_cls01' % prefix)

    for attr in ['scalePivot', 'rotatePivot']:
        cmds.setAttr('%s.%s' % (topClstr[1], attr), -width / 2, 0, 0)
    for attr in ['scalePivot', 'rotatePivot']:
        cmds.setAttr('%s.%s' % (botClstr[1], attr), width / 2, 0, 0)

    cmds.setAttr('%sShape.originX' % topClstr[1], (-width / 2))
    cmds.setAttr('%sShape.originX' % botClstr[1], (width / 2))
    cmds.percent(topClstr[0], '%s.cv[1]' % wireCurve, v=0.5)
    cmds.percent(botClstr[0], '%s.cv[1]' % wireCurve, v=0.5)

    # Create twist and wire blend shape deformers
    twistNode = cmds.nonLinear(flexiBlend, type='twist')
    cmds.wire(flexiBlend, w=wireCurve, dds=[0, 20], foc=0, n='%s_wireAttrs_surface01' % prefix)
    cmds.xform(twistNode, ro=(0, 0, 90))
    twistNode[0] = cmds.rename(twistNode[0], '%s_twistAttrs_surface01' % prefix)
    twistNode[1] = cmds.rename(twistNode[1], '%s_twist_surface01' % prefix)

    # Connect controls to cluster deformers
    cmds.connectAttr('%s.translate' % squareCons[0], '%s.translate' % topClstr[1])
    cmds.connectAttr('%s.translate' % squareCons[1], '%s.translate' % botClstr[1])
    cmds.connectAttr('%s.translate' % squareCons[2], '%s.translate' % midClstr[1])

    # Connect controls to twist deformer
    cmds.connectAttr('%s.rotateX' % squareCons[0], '%s.endAngle' % twistNode[0])
    cmds.connectAttr('%s.rotateX' % squareCons[1], '%s.startAngle' % twistNode[0])

    # Organize hiearchy nodes and groups
    rootGrp = cmds.group(em=1, n='%s01' % prefix)
    moveGrp = cmds.group(em=1, n='%s_globalMove01' % prefix)
    extrasGrp = cmds.group(em=1, n='%s_extraNodes01' % prefix)

    cmds.parent(flexiBlend, folGrp, wireCurve, twistNode[1], clsGrp, '%s_wire_surface01BaseWire' % prefix, extrasGrp)
    cmds.parent(flexiPlane, squareConGrp, moveGrp)
    cmds.parent(moveGrp, extrasGrp, rootGrp)

    # Scale contraint each follicle to global move group
    for fol in cmds.listRelatives(folGrp, c=1):
        cmds.scaleConstraint(moveGrp, fol, mo=0)


# flexiPlaneSetup('spine')
flexiPlaneSetup('base')

print '*** Code Complete ***'
