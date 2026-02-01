from mininet.topo import Topo

class MyTopo(Topo):
    def __init__(self, n=2):
        
        if n < 2:
            raise ValueError("n must be >= 2: at least two switches are required")
        
        Topo.__init__(self)
                
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        h4 = self.addHost('h4')

        switches = []
        for i in range(1, n + 1):
            s = self.addSwitch(f's{i}')
            switches.append(s)

        for i in range(n - 1):
            self.addLink(switches[i], switches[i + 1])

        self.addLink(h1, switches[0])
        self.addLink(h2, switches[0])
        
        self.addLink(h3, switches[-1])
        self.addLink(h4, switches[-1])

topos = {'mytopo': (lambda n=2: MyTopo(n))}
