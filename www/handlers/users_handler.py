#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
 user api handler

'''
import logging;logging.basicConfig(level=logging.INFO)

from coroweb import get, post

from apis import APIError,APIValueError, APIResourceNotFoundError,APIPermissionError

from models import User, next_id

from aiohttp import web

import re,os,json,time,hashlib

from handler import get_page_index,user2cookie
from comm import COOKIE_NAME,_RE_SHA1,_RE_EMAIL,Page

@get('/')
def welcome():
	return {
		'__template__': 'users/signin.html'
	}

@get('/signin')
def signin():
	return {
		'__template__': 'users/signin.html'
	}

@get('/index')
def index(*,page='1'):
	return {
		'__template__': 'index.html',
		'page_index': get_page_index(page)
	}

@get('/user/{id}')
def get_user(id):
	user = yield from User.find(id)
	return {
		'__template__': 'user/user.html',
		'user': user
	}


@get('/api/users')
def api_get_users(*,page='1'):
	page_index = get_page_index(page)
	num = yield from User.findNumber('count(id)',"admin=?",[0])
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, users=())
	users = yield from User.findAll('admin=?',[0],orderBy='created_at desc', limit=(p.offset, p.limit))
	for u in users:
		u.passwd = '******'
		u.status = getUseStatus(users[0].status)

	return dict(page=p,users=users)

@get('/signout')
def signout(request):
	request.__user__ = None
	referer = request.headers.get('Referer')
	r = web.HTTPFound(referer or '/')
	r.set_cookie(COOKIE_NAME,'-deleted-',max_age=0,httponly=True)
	logging.info('user signed out.')
	return r


@get('/register')
def register():
	return {
		'__template__': 'user/register.html'
	}

@post('/api/users')
def api_register_user(*,email,phone,name,passwd):
	if not name or not name.strip():
		raise APIValueError('name')
	if not email or not _RE_EMAIL.match(email):
		raise APIValueError('email')
	if not passwd or not _RE_SHA1.match(passwd):
		raise APIValueError('password')
	users = yield from User.findAll('email=?',[email])
	if len(users) > 0:
		raise APIError('register:failed', 'email', 'Email is already in use.')
	uid = next_id()
	sha1_passwd = '%s:%s' % (uid, passwd)
	user = User(id=uid,name=name.strip(),email=email,phone=phone,passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),admin=0,status=1,avatar='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
	yield from user.save()
	r = web.Response()
	r.set_cookie(COOKIE_NAME,user2cookie(user,86400),max_age=86400,httponly=True)
	user.passwd = '******'
	r.content_type = 'application/json'
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r

@post('/admin/authenticate')
def authenticate(*,email,passwd):
	if not email or not passwd:
		raise APIValueError('email', 'Email or password can not be empty')
	users = yield from User.findAll('email=?',[email])
	if len(users) == 0:
		raise APIValueError('email', 'Email not exist.')
	user = users[0]
	# check passwd:
	sha1 = hashlib.sha1()
	sha1.update(user.id.encode('utf-8'))
	sha1.update(b':')
	sha1.update(passwd.encode('utf-8'))
	if user.passwd != sha1.hexdigest():
		raise APIValueError('passwd', 'Error password.')
	r = web.Response()
	r.set_cookie(COOKIE_NAME,user2cookie(user,86400),max_age=84600,httponly=True)
	user.passwd = '******'
	r.content_type = 'application/json'
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r

@post('/api/user/{id}/action/{status}')
def api_delete_blog(request, *, id,status):
	#check_admin(request)
	user = yield from User.find(id)
	user.status = status
	yield from user.update()
	return dict(id=id)

def getUseStatus(status):
	user_status = "正常"
	if status == "1":
		user_status = "正常"
	elif status == "2":
		user_status = "禁言"
	elif status == "3":
		user_status = "封禁"
	return user_status