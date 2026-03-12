import React,{useState} from 'react'
import {useNavigate} from 'react-router-dom';

const Login=()=>{
    const navigate = useNavigate();
    const [message, setMessage] = useState("");
	const [username,setUsername]=useState(""); 
	const [password,setPassword]=useState(""); 

    let handleSubmit = async (e) => {
        e.preventDefault();
        try {
            let res = await fetch("http://localhost:5000/login", {
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                method: "POST",
                body: JSON.stringify({
                    username:username,
                    password:password,
                }),
            });
            let resJson = await res.json();
                if (res.status === 201) {
                setUsername("");
                setPassword("");
                setMessage(resJson.msg);
                navigate('/tictactoe');
                } else {
                    setMessage(resJson.msg);
                }
        } catch (err) {
          console.log(err);
        }
    };

	return(
	<div>
		<form onSubmit={handleSubmit}> 
			<div> 
				<label htmlFor="username">Username</label>
				<input type="text" name="username" id="username" value={username} onChange={(e)=>setUsername(e.target.value)}/> 
			</div> 
			<div> 
				<label htmlFor="password">Password</label>
			<input type="text" name="password" id="password" value={password} onChange={(e)=>setPassword(e.target.value)}/> 
			</div>
			<button type="submit">Login</button>
            <div className="message">{message ? <p>{message}</p> : null}</div>
            
		</form>
	</div>
)} 

export default Login;