# -*- coding: utf-8 -*-
from PyQt4 import QtCore, QtGui
#from PySide import QtCore, QtGui
from Node import *
import functions
from advancedTypes import OrderedDict
from TreeWidget import *
from DataTreeWidget import *
from FlowchartTemplate import *
from Terminal import Terminal
from numpy import ndarray

def toposort(deps, nodes=None, seen=None, stack=None):
    """Topological sort. Arguments are:
      deps    dictionary describing dependencies where a:[b,c] means "a depends on b and c"
      nodes   optional, specifies list of starting nodes (these should be the nodes 
              which are not depended on by any other nodes) 
    """
    if nodes is None:
        ## run through deps to find nodes that are not depended upon
        rem = set()
        for dep in deps.itervalues():
            rem |= set(dep)
        nodes = set(deps.keys()) - rem
    if seen is None:
        seen = set()
        stack = []
    sorted = []
    for n in nodes:
        if n in stack:
            raise Exception("Cyclic dependency detected", stack + [n])
        if n in seen:
            continue
        seen.add(n)
        sorted.extend( toposort(deps, deps[n], seen, stack+[n]))
        sorted.append(n)
    return sorted
        

class Flowchart(Node):
    def __init__(self, terminals=None, name=None):
        if name is None:
            name = "Flowchart"
        if terminals is None:
            terminals = {}
        Node.__init__(self, name)  ## create node without terminals; we'll add these later
            
        self.nodes = {}
        #self.connects = []
        self._chartGraphicsItem = FlowchartGraphicsItem(self)
        self._widget = None
        self._scene = None
        
        self.inputNode = Node('Input')
        self.outputNode = Node('Output')
        self.addNode(self.inputNode, 'Input', [-150, 0])
        self.addNode(self.outputNode, 'Output', [300, 0])
            
        QtCore.QObject.connect(self.outputNode, QtCore.SIGNAL('outputChanged'), self.outputChanged)
            
        for name, opts in terminals.iteritems():
            self.addTerminal(name, **opts)
      
        
        
    def addTerminal(self, name, **opts):
        name, term = Node.addTerminal(self, name, **opts)
        if opts['io'] == 'in':  ## inputs to the flowchart become outputs on the input node
            opts['io'] = 'out'
            opts['multi'] = True
            self.inputNode.addTerminal(name, **opts)
        else:
            opts['io'] = 'in'
            opts['multi'] = False
            self.outputNode.addTerminal(name, **opts)

    def createNode(self, nodeType, name=None):
        if name is None:
            n = 0
            while True:
                name = "%s.%d" % (nodeType, n)
                if name not in self.nodes:
                    break
                n += 1
                
        node = functions.NODE_LIST[nodeType](name)
        self.addNode(node, name)
        return node
        
    def addNode(self, node, name, pos=None):
        if pos is None:
            pos = [0, 0]
        item = node.graphicsItem()
        item.setParentItem(self.chartGraphicsItem())
        item.moveBy(*pos)
        self.nodes[name] = node
        self.widget().addNode(node)
        
    def arrangeNodes(self):
        
        pass
        
    def internalTerminal(self, term):
        """If the terminal belongs to the external Node, return the corresponding internal terminal"""
        if term.node() is self:
            if term.isInput():
                return self.inputNode[term.name()]
            else:
                return self.outputNode[term.name()]
        else:
            return term
        
    def connect(self, term1, term2):
        """Connect two terminals together within this flowchart."""
        term1 = self.internalTerminal(term1)
        term2 = self.internalTerminal(term2)
        term1.connectTo(term2)
        
        
    def process(self, **args):
        data = {}  ## Stores terminal:value pairs
        
        ## determine order of operations
        ## order should look like [('p', node1), ('p', node2), ('d', terminal1), ...] 
        ## Each tuple specifies either (p)rocess this node or (d)elete the result from this terminal
        order = self.processOrder()
        
        ## Record inputs given to process()
        for n, t in self.inputNode.outputs().iteritems():
            data[t] = args[n]
        
        ret = {}
            
        ## process all in order
        for c, arg in order:
            
            if c == 'p':     ## Process a single node
                #print "process:", arg
                node = arg
                outs = node.outputs().values()
                ins = node.inputs().values()
                #print "  ", outs, ins
                args = {}
                for inp in ins:
                    inputs = inp.inputTerminals()
                    if len(inputs) == 0:
                        continue
                    if inp.isMultiInput():  ## multi-input terminals require a dict of all inputs
                        args[inp.name()] = dict([(i, data[i]) for i in inputs])
                    else:                   ## single-inputs terminals only need the single input value available
                        args[inp.name()] = data[inputs[0]]  
                if node is self.outputNode:
                    ret = args  ## we now have the return value, but must keep processing in case there are other endpoint nodes in the chart
                else:
                    result = node.process(**args)
                    for out in outs:
                        #print "    Output:", out, out.name()
                        #print out.name()
                        try:
                            data[out] = result[out.name()]
                        except:
                            print out, out.name()
                            raise
            elif c == 'd':   ## delete a terminal result (no longer needed; may be holding a lot of memory)
                del data[arg]

        return ret
        
    def setInput(self, **args):
        Node.setInput(self, **args)
        self.inputNode.setOutput(**args)
        
    def outputChanged(self):
        self.widget().outputChanged(self.outputNode.inputValues())
        
    def processOrder(self):
        """Return the order of operations required to process this chart.
        The order returned should look like [('p', node1), ('p', node2), ('d', terminal1), ...] 
        where each tuple specifies either (p)rocess this node or (d)elete the result from this terminal
        """
        
        ## first collect list of nodes/terminals and their dependencies
        deps = {}
        tdeps = {}
        for name, node in self.nodes.iteritems():
            deps[node] = node.dependentNodes()
            for t in node.outputs().itervalues():
                tdeps[t] = t.dependentNodes()
            
        #print "DEPS:", deps
        ## determine correct node-processing order
        #deps[self] = []
        order = toposort(deps)[1:]
        #print "ORDER1:", order
        
        ## construct list of operations
        ops = [('p', n) for n in order]
        
        ## determine when it is safe to delete terminal values
        dels = []
        for t, nodes in tdeps.iteritems():
            lastInd = 0
            lastNode = None
            for n in nodes:
                if n is self:
                    lastInd = None
                    break
                else:
                    ind = order.index(n)
                if lastNode is None or ind > lastInd:
                    lastNode = n
                    lastInd = ind
            #tdeps[t] = lastNode
            if lastInd is not None:
                dels.append((lastInd+1, t))
        dels.sort(lambda a,b: cmp(b[0], a[0]))
        for i, t in dels:
            ops.insert(i, ('d', t))
            
        return ops
        

    def chartGraphicsItem(self):
        """Return the graphicsItem which displays the internals of this flowchart.
        (graphicsItem() still returns the external-view item)"""
        return self._chartGraphicsItem
        
    def widget(self):
        if self._widget is None:
            self._widget = FlowchartWidget(self)
            self.scene = self._widget.scene()
            #self._scene = QtGui.QGraphicsScene()
            #self._widget.setScene(self._scene)
            self.scene.addItem(self.chartGraphicsItem())
        return self._widget

    def listConnections(self):
        conn = set()
        for n in self.nodes.itervalues():
            terms = n.outputs()
            for n, t in terms.iteritems():
                for c in t.connections():
                    conn.add((t, c))
        return conn

    def saveState(self):
        state = Node.saveState(self)
        state['nodes'] = []
        state['connects'] = []
        state['terminals'] = self.saveTerminals()
        
        for name, node in self.nodes.iteritems():
            cls = type(node)
            if hasattr(cls, 'nodeName'):
                clsName = cls.nodeName
                pos = node.graphicsItem().pos()
                ns = {'class': clsName, 'name': name, 'pos': (pos.x(), pos.y()), 'state': node.saveState()}
                state['nodes'].append(ns)
            
        conn = self.listConnections()
        for a, b in conn:
            state['connects'].append((a.node().name(), a.name(), b.node().name(), b.name()))
        
        return state
        
    def restoreState(self, state):
        self.clear()
        Node.restoreState(self, state)
        for n in state['nodes']:
            if n['name'] in self.nodes:
                continue
            node = self.createNode(n['class'], name=n['name'])
            node.restoreState(n['state'])
            node.graphicsItem().moveBy(*n['pos'])
        self.restoreTerminals(state['terminals'])
        for n1, t1, n2, t2 in state['connects']:
            self.connect(self.nodes[n1][t1], self.nodes[n2][t2])

    def clear(self):
        for n in self.nodes.values():
            if n is self.inputNode or n is self.outputNode:
                continue
            self.widget().removeNode(n)
            n.close()
            del self.nodes[n.name()]
        self.clearTerminals()
        self.widget().clear()
        
    def clearTerminals(self):
        Node.clearTerminals(self)
        self.inputNode.clearTerminals()
        self.outputNode.clearTerminals()

class FlowchartGraphicsItem(QtGui.QGraphicsItem):
    def __init__(self, chart):
        QtGui.QGraphicsItem.__init__(self)
        self.chart = chart
        self.updateTerminals()
        
    def updateTerminals(self):
        self.terminals = {}
        bounds = self.boundingRect()
        inp = self.chart.inputs()
        dy = bounds.height() / (len(inp)+1)
        y = dy
        for n, t in inp.iteritems():
            item = t.graphicsItem()
            self.terminals[n] = item
            item.setParentItem(self)
            item.setAnchor(bounds.width(), y)
            y += dy
        out = self.chart.outputs()
        dy = bounds.height() / (len(out)+1)
        y = dy
        for n, t in out.iteritems():
            item = t.graphicsItem()
            self.terminals[n] = item
            item.setParentItem(self)
            item.setAnchor(0, y)
            y += dy
        
    def boundingRect(self):
        return QtCore.QRectF()
        
    def paint(self, p, *args):
        pass
        #p.drawRect(self.boundingRect())
    

class FlowchartWidget(QtGui.QWidget):
    def __init__(self, chart, *args):
        QtGui.QWidget.__init__(self, *args)
        self.chart = chart
        self.items = {}
        self.hoverItem = None
        #self.setMinimumWidth(250)
        #self.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding))
        
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        
        #self.leftWidget = QtGui.QWidget()
        #self.vl = QtGui.QVBoxLayout()
        #self.vl.setSpacing(0)
        #self.vl.setContentsMargins(0,0,0,0)
        #self.leftWidget.setLayout(self.vl)
        #self.nodeCombo = QtGui.QComboBox()
        #self.ctrlList = TreeWidget()
        self.ui.ctrlList.setColumnCount(1)
        self.ui.ctrlList.setColumnWidth(0, 200)
        self.ui.ctrlList.setVerticalScrollMode(self.ui.ctrlList.ScrollPerPixel)
        self.ui.ctrlList.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        #self.vl.addWidget(self.nodeCombo)
        #self.vl.addWidget(self.ctrlList)
        
        #self.addWidget(self.leftWidget)
        #self.view = QtGui.QGraphicsView()
        #self.addWidget(self.view)
        self._scene = QtGui.QGraphicsScene()
        self.ui.view.setScene(self._scene)
        #self.setSizes([200, 1000])
        
        self.ui.nodeCombo.addItem("Add Node..")
       
        for f in functions.NODE_LIST:
            self.ui.nodeCombo.addItem(f)
            
        #self.dataSplitter = QtGui.QSplitter()
        #self.dataSplitter.setOrientation(QtCore.Qt.Vertical)
        #self.addWidget(self.dataSplitter)
        
        #self.outputTree = DataTreeWidget()
        #self.selectTree = DataTreeWidget()
        #self.dataSplitter.addWidget(self.outputTree)
        #self.dataSplitter.addWidget(self.selectTree)
            
        QtCore.QObject.connect(self.ui.nodeCombo, QtCore.SIGNAL('currentIndexChanged(int)'), self.nodeComboChanged)
        QtCore.QObject.connect(self.ui.ctrlList, QtCore.SIGNAL('itemChanged(QTreeWidgetItem*,int)'), self.itemChanged)
        QtCore.QObject.connect(self._scene, QtCore.SIGNAL('selectionChanged()'), self.selectionChanged)
        QtCore.QObject.connect(self.ui.view, QtCore.SIGNAL('hoverOver'), self.hoverOver)
    

    def scene(self):
        return self._scene

    def nodeComboChanged(self, ind):
        if ind == 0:
            return
        nodeType = str(self.ui.nodeCombo.currentText())
        self.ui.nodeCombo.setCurrentIndex(0)
        self.chart.createNode(nodeType)

    def itemChanged(self, *args):
        pass
    
    def addNode(self, node):
        ctrl = node.ctrlWidget()
        if ctrl is None:
            return
        item = QtGui.QTreeWidgetItem([node.name(), '', ''])
        self.ui.ctrlList.addTopLevelItem(item)
        item2 = QtGui.QTreeWidgetItem()
        item.addChild(item2)
        self.ui.ctrlList.setItemWidget(item2, 0, ctrl)
        self.items[node] = item
        
    def removeNode(self, node):
        if node in self.items:
            item = self.items[node]
            self.ui.ctrlList.removeTopLevelItem(item)
            
    def outputChanged(self, data):
        self.ui.outputTree.setData(data, hideRoot=True)

    def selectionChanged(self):
        items = self._scene.selectedItems()
        if len(items) == 0:
            data = None
        else:
            item = items[0]
            if hasattr(item, 'node') and isinstance(item.node, Node):
                n = item.node
                data = {'outputs': n.outputValues(), 'inputs': n.inputValues()}
                self.ui.selNameLabel.setText(n.name())
                if hasattr(n, 'nodeName'):
                    self.ui.selDescLabel.setText("<b>%s</b>: %s" % (n.nodeName, n.desc))
                else:
                    self.ui.selDescLabel.setText("")
                if n.exception is not None:
                    data['exception'] = n.exception
            else:
                data = None
        self.ui.selectedTree.setData(data, hideRoot=True)

    def hoverOver(self, items):
        term = None
        for item in items:
            if item is self.hoverItem:
                return
            self.hoverItem = item
            if hasattr(item, 'term') and isinstance(item.term, Terminal):
                term = item.term
                break
        if term is None:
            self.ui.hoverLabel.setText("")
        else:
            if isinstance(term, ndarray):
                val = term.value()
                val = "%s %s %s" % (type(val).__name__, str(term.shape), str(term.dtype))
            else:
                val = str(term.value())
                if len(val) > 400:
                    val = val[:400] + "..."
            self.ui.hoverLabel.setText("%s.%s = %s" % (term.node().name(), term.name(), val))

    def clear(self):
        self.ui.outputTree.setData(None)
        self.ui.selectedTree.setData(None)
        self.ui.hoverLabel.setText('')
        self.ui.selNameLabel.setText('')
        self.ui.selDescLabel.setText('')
        
        
class FlowchartNode(Node):
    pass

