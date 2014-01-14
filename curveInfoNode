import maya.OpenMaya as om

sel = om.MSelectionList()
sel.add('CpathCurveIKChainSplineShape')
dag = om.MDagPath()
sel.getDagPath(0, dag)

posEnd = om.MPoint(*cmds.xform('locator1', q=1, ws=1, t=1))
posStart = om.MPoint(*cmds.xform('locator2', q=1, ws=1, t=1))


curveFn = om.MFnNurbsCurve(dag)

utilEnd = om.MScriptUtil(0)
ptrEnd = utilEnd.asDoublePtr()

utilStart = om.MScriptUtil(0)
ptrStart = utilStart.asDoublePtr()

curveFn.getParamAtPoint(posEnd, ptrEnd, om.MSpace.kWorld)
curveFn.getParamAtPoint(posStart, ptrStart, om.MSpace.kWorld)

print 'end', om.MScriptUtil.getDouble(ptrEnd)
print 'start', om.MScriptUtil.getDouble(ptrStart)

'''
end 0.123543997297
start 0.333333343193
'''
