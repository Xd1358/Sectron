try:
	import config
except ImportError:
	pass
import sqlite3 as sqlite

def modinit(self):
	self.hostserv = self.createclient(config.hostservnick,config.hostservuser,config.hostservhost,config.hostservgecos)

def onPrivmsg(self,target,uid,nick,host,realhost,account,message):
	if target == self.hostserv:
		msplit = message.split(" ")
		if msplit[0].lower() == "vhost":
			if self.uidstore[uid]['oper']: #If person is Oper,
				try:
					account = msplit[1]
					newhost = msplit[2]
					self.hostservconnect = sqlite.connect('db/nickserv.db')
					self.cursor = self.hostservconnect.cursor()
					self.cursor.execute("CREATE TABLE IF NOT EXISTS accounts (account, password, email, vhost, lastuid)")
					self.hostservconnect.commit()
					self.cursor.execute("UPDATE accounts SET vhost=? WHERE account=?",(newhost, account))
					self.cursor.execute("SELECT * FROM accounts where account=?",(account,))
					for row in self.cursor:
						tuid = row[4]
					self.chghost(tuid, newhost)
					self.sendprivmsg(self.hostserv, self.reportchan, "VHost: Account \x02" + account + "\x02 <=> VHost \x02" + newhost + "\x02")
					self.sendnotice(self.hostserv, uid,"The account you selected has been vhosted.")
					self.hostservconnect.commit()
					self.hostservconnect.close()
				except Exception,e:
					self.sendnotice(self.hostserv, uid, "Syntax: \x02vhost <account> <vhost>\x02")
					print e
			else:
				seld.sendnotice(self.hostserv, uid,"You are not allowed to preform this operation.")

def moddeinit(self):
	self.destroyclient(self.hostserv,"Shutting Down")
