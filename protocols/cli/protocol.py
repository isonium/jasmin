# Copyright 2012 Fourat Zouari <fourat@gmail.com>
# See LICENSE for details.

import string
from twisted.conch import recvline

IDENTCHARS = string.ascii_letters + string.digits + '_'

class CmdProtocol(recvline.HistoricRecvLine):
    """CmdProtocol is a ported/simplified version of cmd module that
    can be served through a socket server
    """
    
    identchars = IDENTCHARS
    motd = 'Welcome !'
    nohelp = "*** No help on %s"
    helpHeaders = {'commands': 'Available commands:', 
                   'baseCommands': 'Control commands:',
                   'ruler': '=',}
    prompt = '>>> '
    nestedApp = None

    baseCommands = ['quit', 'help']
    commands = []
    
    def __init__(self, factory, log):
        recvline.HistoricRecvLine.__init__(self)
        
        self.factory = factory
        self.log = log
        
    def initializeScreen(self):
        'Overrides twisted.conch.recvline.RecvLine.initializeScreen() to not to show prompt'

        self.terminal.reset()
        self.setInsertMode()
        
    def drawInputLine(self):
        'Overrides twisted.conch.recvline.RecvLine.drawInputLine() to reset prompt'

        self.terminal.write(self.prompt + ''.join(self.lineBuffer))
        
    def connectionMade(self):
        recvline.HistoricRecvLine.connectionMade(self)
        
        # Get transport
        transport = self.terminal.transport.transport
        # Get peer
        self.peer = transport.getPeer()
        # Save session to factory
        self.factory.sessionRef+= 1
        self.factory.sessionsOnline+= 1
        self.sessionRef = self.factory.sessionRef
        self.factory.sessions[self.sessionRef] = self
        
        # Welcome to jcli
        self.sendData(self.motd, False)
        self.sendData('Session ref: %s' % self.sessionRef, False)
        
        self.log.info('[sref:%s] Started for %s:%s' % (self.sessionRef, self.peer.host, self.peer.port))
        
    def connectionLost(self, reason):
        recvline.HistoricRecvLine.connectionLost(self, reason)

        self.factory.sessionsOnline-= 1
        del self.factory.sessions[self.sessionRef]
        self.log.info('[sref:%s] Stopped (%s).' % (self.sessionRef, reason.value))
        
    def sendData(self, data = None, prompt = None, append = ''):
        self.log.debug('[sref:%s] Send data: %s' % (self.sessionRef, data))
        
        # Do we have to write some date ?
        if data is not None:
            self.terminal.write(data)
            self.terminal.nextLine()
        
        # Write a new prompt
        if prompt is not False:
            if prompt is None:
                prompt = self.prompt
            self.terminal.write(self.prompt+append)
        # Just append to the current line
        elif append != '':
            self.terminal.write(append)
    
    def parseline(self, line):    
        """Parse the line into a command name and a string containing
        the arguments.  Returns a tuple containing (command, args, line).
        'command' and 'args' may be None if the line couldn't be parsed.
        
        Similar to cmd.Cmd.parseline()
        """
        line = line.strip()
        if not line:
            self.log.debug('[sref:%s] Parsed line returns: cmd=None, agr=None, line=%s' % (self.sessionRef, line))
            return None, None, line
        elif line[0] == '?':
            line = 'help ' + line[1:]

        i, n = 0, len(line)
        while i < n and line[i] in self.identchars: i = i+1
        cmd, arg = line[:i], line[i:].strip()
        
        self.log.debug('[sref:%s] Parsed line returns: cmd=%s, agr=%s, line=%s' % (self.sessionRef, cmd, arg, line))
        return cmd, arg, line
    
    def lineReceived(self, line):
        self.log.debug('[sref:%s] Received line: %s' % (self.sessionRef, line))
        
        cmd, arg, line = self.parseline(line)
        
        if not line:
            return self.sendData()
        if cmd is None or cmd not in self.findCommands():
            return self.default(line)

        funcName = 'do_' + cmd
        try:
            func = getattr(self, funcName)
        except AttributeError:
            return self.default(line)

        self.log.debug('[sref:%s] Running %s with arg:%s' % (self.sessionRef, funcName, arg))
        return func(arg)
    
    def findCommands(self, prefix = None):
        # No prefix finding, return all commands
        if prefix is None:
            return self.commands+self.baseCommands
        
        # Find commands by prefix
        foundCommands = []
        for availableCmd in self.commands+self.baseCommands:
            
            if availableCmd.find(prefix) == 0:
                foundCommands.append(availableCmd)
                
        return foundCommands
    
    def handle_TAB(self):
        line = ''.join(self.lineBuffer)
        self.log.debug('[sref:%s] Tabulation: %s' % (self.sessionRef, line))
        
        cmd, arg, line = self.parseline(line)
        
        if cmd is None:
            # list available commands
            return self.sendData('\n'+' '.join(self.findCommands()))
        elif cmd is not None and arg=='':
            # Complete or list available commands
            completions = self.findCommands(cmd)
            
            # List available commands
            if len(completions) > 1:
                return self.sendData('\n'+' '.join(completions), append = cmd)
            # Complete command name if it is not
            elif len(completions) == 1 and cmd != completions[0]:
                completetion = completions[0]+' '
                self.lineBuffer = list(completetion)
                self.lineBufferIndex = len(self.lineBuffer)
                return self.sendData(data = None, prompt = False, append = completetion[len(cmd):])
        
    def default(self, line):
        self.sendData('Incorrect command: %s, type help for a list of commands' % line)
        
    def do_quit(self, arg):
        'Disconnect from console'
        
        self.terminal.loseConnection()
                
    def do_help(self, arg):
        'List available commands with "help" or detailed help with "help cmd".'

        if arg:
            # Don't provide help for non-exposed commands
            if arg not in self.commands+self.baseCommands:
                return self.sendData("%s" % str(self.nohelp % (arg,)))
                
            # XXX check arg syntax
            DOC = ''
            try:
                # Do we have any docstring ?
                doc = getattr(self, 'do_' + arg).__doc__
                if doc:
                    DOC+= doc

                # Do we have any extended doc from options ?
                extended_doc = getattr(self, 'do_' + arg).__extended_doc__
                if extended_doc:
                    DOC+= '\n'+extended_doc

            except Exception:
                if DOC == '':
                    return self.sendData("%s" % str(self.nohelp % (arg,)))
            
            return self.sendData("%s"%str(DOC))
        else:
            # Get commands first
            helpText = self.helpHeaders['commands']+'\n'+self.helpHeaders['ruler']*len(self.helpHeaders['commands'])
            for cmd in self.commands:
                helpText+= "\n"
                helpText+= '%s\t\t' % cmd
                doc = getattr(self, 'do_' + cmd).__doc__
                if doc:
                    helpText+= str(doc)
                else:
                    helpText+= "%s" % str(self.nohelp % (cmd,))
                
            # Then get baseCommands
            helpText+= '\n\n'+self.helpHeaders['baseCommands']+'\n'+self.helpHeaders['ruler']*len(self.helpHeaders['baseCommands'])
            for cmd in self.baseCommands:
                helpText+= "\n"
                helpText+= '%s\t\t' % cmd
                doc = getattr(self, 'do_' + cmd).__doc__
                if doc:
                    helpText+= str(doc)
                else:
                    helpText+= "%s" % str(self.nohelp % (cmd,))

            return self.sendData(helpText)