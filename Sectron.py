# Sectron IRC Services - Damn well fast IRC Service, at /YOUR/ service!
# ---------------------------------------------------------------------
# Made by Micheal Harker - 2011
# Designed for charybdis - Works on TS6 servers

import asynchat, asyncore, re, socket, time, os, sys, datetime
try:
	import config
except ImportError:
	print "Sectron needs you to make a config.py - Try renaming conf.py.dist to config.py"
	sys.exit(1)
try:
	if config.lang == "en":
		import lang.en as lang
	if config.lang == "fi":
		import lang.fi as lang
except ImportError:
	print "A very weird error occurred with languages. Try help at #Sectron on irc.freenode.net"
	sys.exit(1)
import __sectron__

class sectron(asynchat.async_chat):
	def __init__(self, (host, port, debugmode) ):
		asynchat.async_chat.__init__(self)
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.set_terminator('\r\n')
		self.data = ""
		self.remote = (host, port)
		self.connect(self.remote)
		self.firstSync = 1
		self.modules = {}
		self.uidstore = {}
		self.nickstore = {}
		self.chanstore = {}
		self.serverstore = {}
		self.suid = 100000
		self.version = "Sectron IRC Services Alpha 0.1[TS6]"
		self.reportchan = config.reportchan
		self.onloadmodules  = config.onloadmods
		self.clientn = 0
		self.debug = debugmode
	
	def handle_connect(self):
		self.sendLine("PASS " + str(config.linkpassword) + " TS 6 " + str(config.sid))
		self.sendLine("CAPAB :QS EX IE KLN UNKLN ENCAP TB SERVICES EUID EOPMOD")
		self.sendLine("SERVER " + str(config.servername) + " 1 :" + str(config.serverdesc))
		self.mainclient = self.createclient(config.mainclientnick, config.mainclientuser, config.mainclienthost, config.mainclientgekos)
		self.startSyncTS = time.time()
		if self.onloadmodules != '':
			for modtoload in self.onloadmodules.split(" "):
				module = self.load("M_"+modtoload)
				module.modinit(self)
	def get_data(self):
		r = self.data
		self.data = ''
		return r
	
	def collect_incoming_data(self, data):
		self.data+=data

	def handle_error(self):
		raise
	

	# API Time! (For Modules)
	def sendLine(self, data):
		if self.debug == 1:
			print "{" + str(time.time()) + "} Send: " + str(data)
		self.push(data+'\r\n')

	def report(self,sender,data):
		self.sendprivmsg(sender, self.reportchan, data)

	def getMask(self, uid):
		return self.uidstore[uid]['nick']+"!"+self.uidstore[uid]['user']+"@"+self.uidstore[uid]['host']

	def accountlogin(self, uid, accountname):
		self.sendLine(':'+config.sid+' ENCAP * SU '+uid+' :'+accountname)
		self.uidstore[uid]['account'] = accountname

	def accountlogout(self,uid):
		self.sendLine(':'+config.sid+' ENCAP * SU :'+uid)
		self.uidstore[uid]['account'] = 'None'
		for modname,module in self.modules.items():
			if hasattr(module, "onLogin"):
				module.onLogin(self,uid,oldhost,newhost)
	
	def chghost(self, uid, newhost):
		oldhost = self.uidstore[uid]['host']
		self.sendLine("CHGHOST "+str(uid)+" "+str(newhost))
		self.uidstore[uid]['host'] = str(newhost)
		for modname,module in self.modules.items():
			if hasattr(module, "onChghost"):
				module.onChghost(self,uid,oldhost,newhost)

	def join(self,client,channel):
		self.sendLine(':'+client+' JOIN '+str(time.time())+' '+channel+' +')
		self.sendLine("MODE "+channel+" +o "+client)

	def part(self,client,channel,reason):
		self.sendLine(':'+client+' PART '+channel+' :'+reason)

	def kill(self,client,killee,reason):
		cserver = config.servername
		chost = self.uidstore[client]['host']
		cuser = self.uidstore[client]['user']
		cnick = self.uidstore[client]['nick']
		self.sendLine(":"+client+" KILL "+killee+" :"+cserver+"!"+chost+"!"+cuser+"!"+cnick+" ("+reason+")") #needs work.#
		del self.userstore[killee]

	def createclient(self,cnick,cuser,chost,cgecos):
		self.suid+=1
		cuid = str(config.sid)+str(self.suid)
		#:SID EUID nickname, hopcount, nickTS, umodes, username, visible hostname, IP address, UID, real hostname, account name, gecos
		self.sendLine(':'+str(config.sid)+' EUID '+cnick+' 0 '+str(time.time())+' +ioS '+cuser+' '+chost+' 0.0.0.0 '+cuid+' 0.0.0.0 0 :'+cgecos) 
		self.uidstore[cuid] = {'nick': cnick, 'user': cuser, 'host': chost, 'realhost': chost, 'account': "None", 'oper': True, 'modes': "+iSo", 'channels': [], 'gecos': cgecos}
		self.join(cuid,self.reportchan)
		self.sendLine("MODE "+config.reportchan+" +i ")
		return cuid

	def destroyclient(self,cuid,reason):
		self.sendLine(":"+cuid+" QUIT :"+reason)

	def sendprivmsg(self,sender,target,message):
		self.sendLine(":"+sender+" PRIVMSG "+target+" :"+str(message))

	def sendnotice(self,sender,target,message):
		self.sendLine(":"+sender+" NOTICE "+target+" :"+str(message))

	def reload(self,modname):
		self.unload(modname)
		self.load(modname)

	def load(self,modname):
		oldpath = list(sys.path)
		sys.path.insert(0, "modules/")
		self.modules["modules/"+modname] = __import__(modname)
		self.modules["modules/"+modname].modinit(self)
		return self.modules[modname]
		sys.path[:] = oldpath
	
	def unload(self,modname):
		self.modules["modules/"+modname].moddeinit(self)
		del self.modules["modules/"+modname]

	# API END :(
	def found_terminator(self):
		data=self.get_data()
		split = str(data).split(" ")
		if self.debug == 1:
			print "{"+str(time.time())+"} Recv: "+data
		if split[0] == "PING":
			self.sendLine("PONG "+split[1])
			if self.firstSync == 1:
				synctime = float(time.time()) - float(self.startSyncTS)
				self.sendLine("WALLOPS :Synced with network in "+str(synctime)[:4]+" seconds.")
				self.firstSync = 0
		elif split[1] == "EUID":
			modes = split[5].strip("+").strip("-")
			nick = split[2]
			user = split[6]
			host = split[7]
			server = split[0].strip(":")
			gecos = ' '.join(split[12:]).strip(":")
			if split[10] == "*":
				realhost = split[7]
			else:
				realhost = split[10]
			ip = split[8]
			uid = split[9]
			account = split[11]
			if account == "*":
				account = "None"
			self.nickstore[nick] = {'uid': uid}
			if "o" in modes:
				self.uidstore[uid] = {'nick': nick, 'user': user, 'host': host, 'realhost': realhost, 'account': account, 'oper': True, 'modes': modes, 'channels': [], 'gecos': gecos, 'ip': ip, 'server': server}
			else:
				self.uidstore[uid] = {'nick': nick, 'user': user, 'host': host, 'realhost': realhost, 'account': account, 'oper': False, 'modes': modes, 'channels': [], 'gecos': gecos, 'ip': ip, 'server': server}
			self.serverstore[server]['users'].append(uid)
			for modname,module in self.modules.items():
				if hasattr(module, "onConnect"):
					module.onConnect(self,uid)
		elif split[0] == "PASS": #add uplink to serverstore
			self.uplinkSID = split[4].strip(":")
			#Do this after we get the server info! --- self.serverstore[SID] = {"servername": servername, "SID": SID, "serverdesc": serverdesc, "users": []}
		elif split[0] == "SERVER":
			self.uplinkservername = split[1]
			self.uplinkserverdesc = ' '.join(split[3:]).strip(":")
			self.serverstore[self.uplinkSID] = {"servername": self.uplinkservername, "SID": self.uplinkSID, "serverdesc": self.uplinkserverdesc, "users": []}
		elif split[1] == "SID":
			servername = split[2]
			SID = split[4]
			serverdesc = ' '.join(split[5:]).strip(':')
			self.serverstore[SID] = {"servername": servername, "SID": SID, "serverdesc": serverdesc, "users": []}
		elif split[1] == "WHOIS": #Incoming WHOIS for a pseudo-client.
			cuid = split[0].strip(":")
			uid = split[2]
			self.sendLine(":"+config.sid+" 311 "+cuid+" "+self.uidstore[uid]['nick']+" "+self.uidstore[uid]['user']+" "+self.uidstore[uid]['host']+" * :"+self.uidstore[uid]['gecos'])
			self.sendLine(":"+config.sid+" 312 "+cuid+" "+self.uidstore[uid]['nick']+" "+config.servername.replace("(H) ","")+" :"+config.serverdesc)
			self.sendLine(":"+config.sid+" 313 "+cuid+" "+self.uidstore[uid]['nick']+" :is a Network Service")
			self.sendLine(":"+config.sid+" 318 "+cuid+" "+self.uidstore[uid]['nick']+" :End of WHOIS")
		elif split[1] == "MOTD": #MOTD handling
			if split[2].strip(":") == config.sid:
				uid = split[0].strip(":")
				self.sendLine(":"+config.sid+" 375 "+uid+" :- "+config.servername+" Message of the day -")
				try:
					f = open("motd.txt","r")
					fread = f.read()
					f.close()
					freads = fread.split("\n")
					for line in freads:
						self.sendLine(":"+config.sid+" 372 "+uid+" :- "+line)
					self.sendLine(":"+config.sid+" 376 "+uid+" :End of the Message of the Day.")
				except:
					self.sendLine(":"+config.sid+" 372 "+uid+" :- No Message of the Day found.")
					self.sendLine(":"+config.sid+" 376 "+uid+" :End of the Message of the Day.")
		elif split[1] == "STATS" and split[3].strip(":") == config.sid: #/stats handling.
			uid = split[0].strip(":")
			request = split[2]
			if request == "u": #/stats u for uptime.
				uptime = datetime.timedelta(seconds=time.time())-datetime.timedelta(seconds=self.startts)
				self.sendLine(":"+config.sid+" 242 "+uid+" :Services uptime: "+str(uptime))
				self.sendLine(":"+config.sid+" 219 "+uid+" :End of /STATS report")
		elif split[0] == "SQUIT":
		 try:
			SID = split[1]
			for uid in self.serverstore[SID]['users']:
				nick = self.uidstore[uid]['nick']
				for channel in self.uidstore[uid]['channels']:
					if len(self.chanstore[channel]['uids']) == 1: #Nobody left in the channel
						del self.chanstore[channel]
					else:
						self.chanstore[channel]['nicks'].remove(nick)
						self.chanstore[channel]['uids'].remove(uid)
				del self.uidstore[uid]
				del self.nickstore[nick]
			del self.serverstore[SID]
		 except Exception,e:
			 self.report(self.mainc,"SQUIT "+SID+" failed: "+str(e))
		elif split[1] == "SJOIN":
			chandata = re.match("^:[A-Z0-9]{3} SJOIN (\d+) (#[^ ]*) (.*?) :(.*)$", data).groups()
			channel = chandata[1]
			uids = chandata[3]
			print uids
			if uids == "@42AAAAAAB":
				self.jstokerstore.append(channel)
			if self.chanstore.has_key(channel):
				for uid in uids.strip("+").strip("@").split(" "):
					uidstrip = uid.replace("@","").replace("+","")
					if uidstrip == '':
						pass
					else:
						nick = self.uidstore[uidstrip]['nick']
						self.chanstore[channel]['nicks'].append(nick)
						self.chanstore[channel]['uids'].append(uid)
			else:
				self.chanstore[channel] = {'ts': chandata[0], 'modes': str(chandata[2]).strip("+"), 'uids': [], 'nicks': []}
				for uid in uids.strip("+").strip("@").split(" "):
					uidstrip = uid.replace("@","").replace("+","")
					if uidstrip == '':
						pass
					else:
						nick = self.uidstore[uidstrip]['nick']
						self.uidstore[uidstrip]['channels'].append(channel)
						self.chanstore[channel]['nicks'].append(nick)
						self.chanstore[channel]['uids'].append(uid)
		elif split[1] == "ENCAP":
			if split[3] == "OPER":
				uid = split[0].replace(":","")
				self.uidstore[uid]['oper'] = True
			elif split[3] == "SU":
				try:
					uid = split[4]
					newaccount = split[5].replace(":","")
					self.uidstore[uid]['account'] = newaccount
					for modname,module in self.modules.items():
						if hasattr(module, "onLogin"):
							module.onLogin(self,uid,oldhost,newhost)
				except:
					pass
		elif split[1] == "JOIN":
			try:
				uid = split[0].replace(":","")
				channel = split[3]
				nick = self.uidstore[uid]['nick']
				self.uidstore[uid]['channels'].append(channel)
				self.chanstore[channel]['nicks'].append(nick)
				self.chanstore[channel]['uids'].append(uid)
				for modname,module in self.modules.items():
					if hasattr(module, "onJoin"):
						module.onJoin(self,uid,channel)
			except: pass
		elif split[1] == "PART":
                 try:
			uid = split[0].replace(":","")
			channel = split[2]
			nick = self.uidstore[uid]['nick']
			for modname,module in self.modules.items():
				if hasattr(module, "onPart"):
					module.onPart(self,uid,channel)
			if len(self.chanstore[channel]['uids']) == 1: #Nobody left in the channel
				del self.chanstore[channel]
			else:
				self.uidstore[uid]['channels'].remove(channel)
				self.chanstore[channel]['nicks'].remove(nick)
				self.chanstore[channel]['uids'].remove(uid)
                 except: pass
		elif split[1] == "CHGHOST":
			uid = split[2]
			oldhost = self.uidstore[uid]['host']
			newhost = split[3]
			self.uidstore[uid]['host'] = split[3]
			for modname,module in self.modules.items():
				if hasattr(module, "onChghost"):
					module.onChghost(self,uid,oldhost,newhost)
		elif split[1] == "NICK":
			try:
				uid = split[0].replace(":","")
				oldnick = self.uidstore[uid]['nick']
				newnick = split[2]
				del self.nickstore[oldnick]
				self.nickstore[newnick] = {'uid': uid}
				for channel in self.uidstore[uid]['channels']:
					self.chanstore[channel]['nicks'].remove(self.uidstore[uid]['nick'])
					self.chanstore[channel]['nicks'].append(newnick)
				self.uidstore[uid]['nick'] = newnick
				for modname,module in self.modules.items():
					if hasattr(module, "onNickChange"):
						module.onNickChange(self,uid,oldnick,newnick)
			except: pass
		elif split[1] == "TMODE": #channel modes
			target = split[3]
			uid = split[0].strip(":")
			ts = split[2]
			modes = split[4]
			if split[5] == '': #Don't process the mode if it has args
				if "+" in modes:
					curmodes = self.chanstore[target]['modes']
					self.chanstore[target]['modes'] = curmodes+modes.strip("+")
				elif "-" in modes:
					removedmode = modes.strip("-")
					self.chanstore[target]['modes'] = self.chanstore[target]['modes'].strip(removedmode)
		elif split[1] == "MODE": #user modes
			target = split[2]
			uid = split[0].strip(":")
			rmodes = split[3].strip(":")
			modes = rmodes.strip("+").strip("-")
			modetype = rmodes[0]
			if modetype == "+":
				self.uidstore[target]['modes'] = self.uidstore[target]['modes']+modes
			if modetype == "-":
				self.uidstore[target]['modes'] = self.uidstore[target]['modes'].strip(modes)
				if "o" in modes:
					self.uidstore[target]['oper'] = False
		elif split[1] == "QUIT":
			try:
				uid = split[0].replace(":","")
				for modname,module in self.modules.items():
					if hasattr(module, "onQuit"):
						module.onQuit(self,uid)
				for channel in self.uidstore[uid]['channels']:
					self.chanstore[channel]['nicks'].remove(self.uidstore[uid]['nick'])
					self.chanstore[channel]['uids'].remove(uid)
				self.serverstore[self.uidstore[uid]['server']]['users'].remove(uid)
				del self.nickstore[self.uidstore[uid]['nick']]
				del self.uidstore[uid]
			except:
				pass       
                elif split[1] == "KILL":
                 try:   
                        uid = split[2]
                        for channel in self.uidstore[uid]['channels']:
                                self.chanstore[channel]['nicks'].remove(self.uidstore[uid]['nick'])
                                self.chanstore[channel]['uids'].remove(uid)
			#self.serverstore[self.uidstore[uid]['server']]['users'].remove(uid)
			#del self.nickstore[self.uidstore[uid]['nick']]
			#del self.uidstore[uid]
			for modname,module in self.modules.items():
				if hasattr(module, "onQuit"):
					module.onQuit(self,uid)
			self.serverstore[self.uidstore[uid]['server']]['users'].remove(uid)
			del self.nickstore[self.uidstore[uid]['nick']]
			del self.uidstore[uid]

                 except: pass			
		#:SID EUID nickname, hopcount, nickTS, umodes, username, visible hostname, IP address, UID, real hostname, account name, gecos
		elif split[1] == "NOTICE" and self.firstSync == 0:
				target = split[2]
				message = data.split("NOTICE "+target+" :")[1]
				uid = split[0].replace(":","")
				for modname,module in self.modules.items():
					if hasattr(module, "onNotice"):
						module.onNotice(self,uid,target,message)
		elif split[1] == "PRIVMSG":
			target = split[2]
			message = data.split("PRIVMSG "+target+" :")[1]
			uid = split[0].replace(":","")
			nick = self.uidstore[uid]['nick']
			host = self.uidstore[uid]['host']
			user = self.uidstore[uid]['user']
			account = self.uidstore[uid]['account']
			realhost = self.uidstore[uid]['realhost']
			oper = self.uidstore[uid]['oper']
			splitm = message.split(" ")
			for modname,module in self.modules.items():
				if hasattr(module, "onPrivmsg"):
					module.onPrivmsg(self,target,uid,nick,host,realhost,account,message)
			#CTCP version replies
			if target[0] != "#":
				if message == "\x01VERSION\x01":
					self.sendLine(":"+target+" NOTICE "+uid+" :\x01VERSION "+self.version+"\x01")
			if splitm[0].lower() == "modload" and self.uidstore[uid]['oper'] == True and target == self.mainc:
				try:
					modtoload = splitm[1]
					self.sendNotice(self.mainc,config.reportchan,"Loading "+str(modtoload)+" (requested by "+nick+"!"+user+"@"+host+")")
					module = self.load("module_"+modtoload)
					module.modinit(self)
				except Exception,e:
					self.sendNotice(self.mainc,config.reportchan,"ERROR: "+(str(e)))
				#TODO: Reload/unload
			elif splitm[0].lower() == "modlist" and self.uidstore[uid]['oper'] == True and target == self.mainc:
				#modname = splitm[1]
				#del self.modules[modname]
				self.sendNotice(self.mainc,config.reportchan,"Modules: "+str(self.modules.keys()))
			elif splitm[0].lower() == "modunload" and self.uidstore[uid]['oper'] == True and target == self.mainc:
				try:
					modname = splitm[1]
					self.modunload(modname)
					self.sendNotice(self.mainc,config.reportchan,"Unloaded "+modname+" (requested by "+nick+"!"+user+"@"+host+")")
				except Exception,e:
					self.sendNotice(self.mainc,config.reportchan,"ERROR: "+(str(e)))
			elif splitm[0].lower() == "modfullreload" and self.uidstore[uid]['oper'] == True and target == self.mainc:
				try:
					modname = splitm[1]
					self.modules["module_"+modname].moddeinit(self)
					reload(self.modules["module_"+modname])
					self.modules["module_"+modname].modinit(self)
					self.sendNotice(self.mainc,config.reportchan,"Reloaded "+modname+" (requested by "+nick+"!"+user+"@"+host+")")
				except Exception,e:
					self.sendLine("NOTICE "+uid+" :ERROR Reloading: "+(str(e)+" (is the module loaded?)"))
			#Reload without using modinit/deinit
			elif splitm[0].lower() == "modreload" and self.uidstore[uid]['oper'] == True and target == self.mainc:
				try:
					modname = splitm[1]
					reload(self.modules["module_"+modname])
					self.sendNotice(self.mainc,config.reportchan,"Reloaded "+modname+" (requested by "+nick+"!"+user+"@"+host+")")
				except Exception,e:
					self.sendLine("NOTICE "+uid+" :ERROR Reloading: "+(str(e)+" (is the module loaded?)"))
			elif splitm[0].lower() == "debugm" and self.uidstore[uid]['oper'] == True and target == self.mainc:
				if splitm[1].lower() == "on":
					self.debug=1
					self.sendNotice(self.mainc,config.reportchan,""+self.uidstore[uid]['nick']+" debug:ON")
				else:# splitm[1].lower() == "off":
					self.sendNotice(self.mainc,config.reportchan,""+self.uidstore[uid]['nick']+" debug:OFF")
					self.debug=0
			elif splitm[0].lower() == "d-exec":# and host == "FOSSnet/staff/bikcmp": #Do *NOT* enable this on a production network.  Used for debugging ONLY.  
				try:
					query = message.split('d-exec ')[1]
					ret=str(eval(query))
					if "#" in target:
						self.sendLine("NOTICE "+target+" :Debug: "+ret)
					else:
						self.sendLine("NOTICE "+uid+" :Debug: "+ret)
				except Exception,e:
					if "#" in target:
						self.sendLine("NOTICE "+target+" :Debug ERROR: "+str(e))
					else:
						self.sendLine("NOTICE "+uid+" :Debug ERROR: "+str(e))

#		else:
		for modname,module in self.modules.items():
								if hasattr(module, "onRaw"): #Warning: don't EVER use this unless you're *SURE* there's not a hook for whatever you're doing.
									module.onRaw(self,data,split)

if __name__ == '__main__':
	debug = 1
	for arg in sys.argv[1:]:
		if " " not in arg and "python" not in arg and "sectron.py" not in arg:
			if arg == "-d":
				debug = 1
				print "Starting Sectron in debug mode."
			else:
				print "Unknown argument: "+arg+" - ignoring"
	print "Sectron started.  PID: "+str(os.getpid())
	sectron((config.linkip, config.linkport, debug))
	asyncore.loop()
