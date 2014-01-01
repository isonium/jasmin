# Copyright 2012 Fourat Zouari <fourat@gmail.com>
# See LICENSE for details.

from jasmin.protocols.cli.protocol import CmdProtocol
from jasmin.protocols.cli.options import options
from jasmin.protocols.cli.managers import UserManager, GroupManager, RouterManager, SmppcmManager
from optparse import make_option

class JCliProtocol(CmdProtocol):
    motd = 'Welcome to Jasmin console\nType help or ? to list commands.\n'
    CmdProtocol.commands.extend(['user', 'group', 'router', 'smppcm'])
    prompt = 'jcli : '
    
    def __init__(self, factory, log):
        CmdProtocol.__init__(self, factory, log)
        
        self.managers = {'user': UserManager(), 'group': GroupManager(), 
                         'router': RouterManager(), 'smppcm': SmppcmManager(), }
        
    def manageModule(self, moduleName, arg, opts):
        if opts.list is None and opts.add is None and opts.remove is None:
            return self.sendData('Missing required option: --list, --add or --remove')
        
        if opts.list:
            return self.sendData(self.managers[moduleName].list())
        if opts.add:
            return self.sendData(self.managers[moduleName].add(arg, opts))
        if opts.remove:
            return self.sendData(self.managers[moduleName].remove(arg, opts))

    @options([make_option('-l', '--list', action="store_true",
                          help="List users"),
              make_option('-a', '--add', action="store_true",
                          help="Add user"),
              make_option('-r', '--remove', action="store_true",
                          help="Remove user"),], '')    
    def do_user(self, arg, opts):
        'User management'
        self.manageModule('user', arg, opts)
        
    @options([make_option('-l', '--list', action="store_true",
                          help="List groups"),
              make_option('-a', '--add', action="store_true",
                          help="Add group"),
              make_option('-r', '--remove', action="store_true",
                          help="Remove group"),], '')    
    def do_group(self, arg, opts):
        'Group management'
        self.manageModule('group', arg, opts)
        
    def do_router(self, arg, opts = None):
        'Router management'
        self.manageModule('router', arg, opts)
        
    @options([make_option('-l', '--list', action="store_true",
                          help="List SMPP connectors"),
              make_option('-a', '--add', action="store_true",
                          help="Add SMPP connector"),
              make_option('-r', '--remove', action="store_true",
                          help="Remove SMPP connector"),], '')    
    def do_smppcm(self, arg, opts):
        'SMPP connector management'
        self.manageModule('smppcm', arg, opts)