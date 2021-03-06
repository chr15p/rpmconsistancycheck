#!/usr/bin/python
# Copyright (C) 2013 Chris Procter 
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os
import sys
import yum
import xmlrpclib
import rpmUtils.transaction
from rpmUtils.miscutils import splitFilename
from optparse import OptionParser

class ConsistancyChecker:
	def __init__(self,repolist):
		ts = rpmUtils.transaction.initReadOnlyTransaction()
		self.yb = yum.YumBase()
		self.yb.setCacheDir()

		if len(repolist) > 0:
			self.yb.repos.disableRepo('*')
			for repo in repolist:
				self.addRepos(repo)

		self.yb.pkgSack = self.yb.repos.populateSack(which='enabled')
		self.repoobjlist=dict()
		for i in self.yb.pkgSack:
			self.repoobjlist["%s-%s-%s.%s"%(i.name, i.version, i.release,i.arch)]=i

		self.testsack = yum.packageSack.PackageSack()

	def getTestSack(self):
		return self.testsack

	def addRepos(self,repo):
		r = repo.split(',',1)
		if not self.yb.repos.findRepos(r[0]):
			newrepo = yum.yumRepo.YumRepository(r[0])
			newrepo.metadata_expire = 0
			if len(r) == 2:
				#newrepo.baseurl="file:///home/chrisp/projects/rpmconsistancycheck/19/fedora-clone/"
				newrepo.baseurl=r[1]
			newrepo.timestamp_check = False
			self.yb.repos.add(newrepo)

		self.yb.repos.enableRepo(r[0])


	def buildTestSackFromFile(self,filelist):
		for filename in filelist:
			rpmlist = self.parsePkgFile(filename)
			for i in rpmlist:
				obj = self.repoobjlist.get(i,"")
				if obj != "":
					self.testsack.addPackage(obj)
				else:
					print "NOT FOUND IN REPOs: " + i
		return self.testsack


	def buildTestSackFromList(self,rpmlist):
		for i in rpmlist:
			obj = self.repoobjlist.get(i,"")
			if obj != "":
				self.testsack.addPackage(obj)
			else:
				print "NOT FOUND IN REPOs: " + i
		return self.testsack


	def parsePkgFile(self,filename):
		pkglist = []
		for line in open(filename):
			pkgname=line.rstrip('\n')
			if pkgname == "": continue
			if pkgname[0] == "#": continue

			if pkgname[-4:] == ".rpm":
				pkglist.append(pkgname[:-4])
			else:
				pkglist.append(pkgname)
		return pkglist

	def removeOld(self):
		self.testsack = self.testsack.returnNewestByNameArch()

	def getNewest(self):
		return yum.packageSack.ListPackageSack(Objlist=self.testsack.returnNewestByNameArch())

	def getDeps(self,sack):
		try:
			deps = self.yb.findDeps(sack)
		except Exception , e:
			print e
			sys.exit(0)

		return deps

	def missingDeps(self,deps,outputsack):
		pkgs=dict()
		for i in deps.keys():				### packages
			for j in deps[i].keys():		### requirements for package
				if deps[i][j] == []:		### no requirements
					continue

				for k in deps[i][j]:        ### potential resolutions for requirements
					if outputsack.searchPO(k):
						break
				else:
					tmpsack = yum.packageSack.ListPackageSack(deps[i][j])
					pkgs[i]=tmpsack.returnNewestByNameArch()

		return pkgs


filename=""
errval=0
parser = OptionParser()
parser.add_option("-e", "--errata", action="store", default=None, dest="errata", help='name of errata to check')
parser.add_option("-r", "--repo", action="append", default=None, dest="repolist", help='id of a repo to check against')

(opt,args) = parser.parse_args()
errata = opt.errata or sys.exit(1)
repolist = opt.repolist or []


SATELLITE_URL = "https://rhn.redhat.com/rpc/api"
SATELLITE_LOGIN = ""
SATELLITE_PASSWORD = ""
client = xmlrpclib.Server(SATELLITE_URL, verbose=0)
key = client.auth.login(SATELLITE_LOGIN, SATELLITE_PASSWORD)

print errata
erratalist=client.errata.listPackages(key,errata)
checker = ConsistancyChecker(repolist)
erratasack = checker.buildTestSackFromList(["%s-%s-%s.%s"%(i["package_name"], i["package_version"], i["package_release"],i["package_arch_label"]) for i in erratalist])
deps = checker.getDeps(erratasack)

depsack = yum.packageSack.PackageSack()
for i in deps.keys():               ### packages
	for j in deps[i].keys():        ### requirements for package
		if deps[i][j] == []: continue

		for k in deps[i][j]: 
			depsack.addPackage(obj)

errata=dict()
newlist = depsack.returnNewestByNameArch()
for i in newlist:
	(name, ver, rel, epoch, arch ) = rpm.miscutils.splitFilename(i)
	pkg = client.packages.findByNvrea(key,i.name,i.ver, i.rel, i.epoch,i.arch)
	errarr=client.packages.listProvidingErrata(key,pkg["id"])
	errata[errarr[0]["advisory"]]=pkg[0]["name"]


for i in errata.keys():
	print i + " ("+ errata[i] +")"

sys.exit(errval)
