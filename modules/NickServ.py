# Sectron IRC Services - Damn well fast IRC Service, at /YOUR/ service!
# ---------------------------------------------------------------------
# Made by Micheal Harker - 2011
# Designed for charybdis - Works on TS6 servers
# ---------------------------------------------------------------------
# NICKSERV Module for Sectron. By Micheal Harker

import hashlib
try:
	import config
except ImportError:
	pass
import sqlite3 as sqlite
try:
	if config.lang == "en":
		import lang.en as lang
except ImportError:
	print "Weird Error importing Languages. Please come to #Sectron on irc.freenode.net for help"
	sys.exit(1)

def modinit(self):
	self.nickserv = self.createclient(config.nickservnick,config.nickservuser,config.nickservhost,config.nickservgecos)
	self.nickservconnect = sqlite.connect('db/nickserv.db')
	self.cursor = self.nickservconnect.cursor()
	self.cursor.execute("CREATE TABLE IF NOT EXISTS accounts (account, password, email, vhost, lastuid)")
	self.nickservconnect.commit()

def onPrivmsg(self,target,uid,nick,host,realhost,account,message):
	if target == self.nickserv:
		msplit = message.split(" ")
		if msplit[0].lower() == "register":
			try:
				self.nickservconnect = sqlite.connect('db/nickserv.db')
				self.cursor = self.nickservconnect.cursor()
				account = self.uidstore[uid]['nick']
				password = msplit[1]
				email = msplit[2]
				if len(self.cursor.execute("SELECT * FROM accounts where account=?",(account,)).fetchall())>0:
					self.sendnotice(self.nickserv,uid,lang.IS_ALREADY_REGGED % account)
				else:
					pwhash = str(hashlib.sha512(password).hexdigest())
					self.sendprivmsg(self.nickserv, self.reportchan, "Register: \x02" + account + "\x02")
					if "@" in email:
						self.cursor.execute("INSERT INTO accounts VALUES (?,?,?,?,?)",(account,pwhash,email,"None",uid))
						self.nickservconnect.commit()
						self.accountlogin(uid, account)
						self.sendnotice(self.nickserv, uid, lang.REGISTER_SUCCESS)
					elif "@" not in email:
						self.sendnotice(self.nickserv,uid,lang.REGISTER_E_EMAIL)
				self.nickservconnect.close()
			except Exception,e:
				self.sendnotice(self.nickserv,uid,"Syntax: \x02register <password> <email>\x02 (Please do NOT include 	<>'s)")
		elif msplit[0].lower() == "login" or msplit[0].lower() == "identify" or msplit[0].lower() == "id":
			try:
				self.nickservconnect = sqlite.connect('db/nickserv.db')
				self.cursor = self.nickservconnect.cursor()				
				account = self.uidstore[uid]['nick']
				password = msplit[1]
				pwhash = str(hashlib.sha512(password).hexdigest())
				self.cursor.execute("SELECT * FROM accounts WHERE account=?",(account,))
#				self.cursor.execute("UPDATE accounts SET lastuid=? WHERE account=?",(uid, account))
				self.nickservconnect.commit()
				for row in self.cursor:
					if row[1] == pwhash:
						self.accountlogin(uid,account)
						if row[3] == "None":
							pass
						else:
							self.chghost(uid,str(row[3]))
						self.sendnotice(self.nickserv,uid,lang.IDENTIFY_SUCCESS % account)
					else:
						self.sendnotice(self.nickserv,uid,"Invalid Password.")
				self.nickservconnect.close()
			except Exception,e:
				self.sendnotice(self.nickserv,uid,"Syntax: \x02" + msplit[0] + " <password>\x02")
				print e
		elif msplit[0].lower() == "logout":
			self.accountlogout(uid)
			self.sendnotice(self.nickserv,uid,"You are now logged out.")
		elif msplit[0].lower() == "help":
			self.sendnotice(self.nickserv,uid,"\x02***NickServ Help***\x02")
			self.sendnotice(self.nickserv,uid,"\x02NickServ\x02 allows you to 'register' a nickname, it is not needed to use it, but ")
			self.sendnotice(self.nickserv,uid,"it is needed to claim it is yours. The following help is avalible:")
			self.sendnotice(self.nickserv,uid,"\x02HELP\x02    Displays this info.")
			self.sendnotice(self.nickserv,uid,"\x02REGISTER\x02    Registres your Nick.")
			self.sendnotice(self.nickserv,uid,"\x02IDENTIFY\x02    Logs you into nickserv.")
			self.sendnotice(self.nickserv,uid,"\x02LOGOUT\x02    Logs you out of nickserv.")
def moddeinit(self):
	
	self.destroyclient(self.nickserv,"Shutting Down")
						
