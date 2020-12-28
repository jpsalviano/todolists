# TodoLists  

A personal todo lists manager web app written in Python.
  
This is an ongoing project for practicing web development.

## Development Roadmap

### 1 - user registration  
	1.1 - view registration form
	1.2 - submit registration form
		1.2.1 - save info to database: user not verified
		1.2.2 - user info validation
		1.2.3 - password encryption
	1.3 - redirect to email verification
	1.4 - failure pages
		1.4.1 - verified email already in use
		1.4.2 - name contains forbidden chars
		1.4.3 - password too short
		1.4.4 - password too long
  
### 2 - email verification  
	2.1 - create token
	2.2 - save token to redis
	2.3 - send email  
	2.4 - endpoint for checking token  
		2.4.1 - update database: user registered  
		2.4.2 - redirect to dashboard  
	2.5 - failure pages
		2.5.1 - wrong token
		2.5.2 - expired token  
  
### 3 - user authentication  
	3.1 - authentication form  
	3.2 - endpoint post - create session with token on redis (token user_id)  
		3.2.1 - check database for password validation
		3.2.2 - check database for verified state
		3.2.3 - create token
		3.2.4 - get user_id from database
		3.2.5 - on redis set key=token value=user_id
		3.2.6 - set cookie ("session-token": token) 
	3.3 - protect private endpoints - a function that takes cookie and returns user_id, else raise 401
	3.4 - logout - delete session on redis and unset cookie on user browser
	3.5 - session for non-verified user (generate new token to verify email)
  
### 4 - creating/editing todo lists  
	4.1 - create todo list  
	4.2 - delete todo list  
  
### 5 - creating/editing tasks  
	5.1 - create task  
	5.2 - delete task  
	5.3 - mark as done  
