#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
 comment api handler

'''

from apis import APIError,APIValueError,APIResourceNotFoundError,APIPermissionError

from coroweb import get, post
from handler import get_page_index

from models import Blog,Comment

from comm import Page

@get('/manage/comments')
def manage_comments(*,page='1'):
	return {
		'__template__': 'comments/manage_comments.html',
		'page_index': get_page_index(page)
	}

@post('/api/blogs/{id}/comments')
def api_create_comment(id,request,*,content):
	user = request.__user__
	if user is None:
		raise APIPermissionError('Please signin first.')
	if not content or not content.strip():
		raise APIValueError('content')
	blog = yield from Blog.find(id)
	if blog is None:
		raise APIResourceNotFoundError('Blog')
	comment = Comment(blog_id=blog.id, user_id=user.id, content=content.strip())
	yield from comment.save()
	return comment

@get('/api/comments')
def api_comments(*, page='1'):
	page_index = get_page_index(page)
	num = yield from Comment.findNumber('count(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, comments=())
	#comments = yield from Comment.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
	sql = " ".join(['SELECT c.* ,u.`name` AS user_name, u.`avatar` FROM `comments` c',
						'LEFT JOIN users u ON c.`user_id` = u.`id`',
						'GROUP BY c.`id`',
						'ORDER BY c.`created_at` DESC',
						'LIMIT %s,%s'%(p.offset, p.limit)])
	comments = yield from Comment.unionSelect(sql)
	return dict(page=p, comments=comments)

@post('/api/comments/{id}/delete')
def delete_comments(request, *, id):
	comment = yield from Comment.find(id)
	yield from comment.remove()
	return dict(id=id)