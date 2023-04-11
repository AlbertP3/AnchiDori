
export async function authenticateUser(username, password) {
    let res = await fetch('/auth', {
                method: 'POST',
                body: JSON.stringify({'username': username, 'password': password})
                })
    let data = await res.json();
    return data
}

export async function getDashboard(username, token) {
    let data = {};
    let res = await fetch('/get_dashboard', {
                method: 'POST',
                body: JSON.stringify({'username': username, 'token': token}),
                })
    try {
        data = await res.json();
    } catch (error){
        console.error(error)
    }
    return data
}

export async function getAllQueries(username, token) {
    let data = {};
    let res = await fetch('/get_all_queries', {
                method: 'POST',
                body: JSON.stringify({'username': username, 'token': token}),
                })
    try {
        data = await res.json();
    } catch (error){
        console.error(error)
    }
    return data
}

export async function addQuery(username, token, query_data) {
    let data = {};
    query_data['username'] = username
    query_data['token'] = token
    let res = await fetch('/add_query', {
                method: 'POST',
                body: JSON.stringify(query_data),
                })
    try {
        data = await res.json();
    } catch (error){
        console.error(error)
    }
    return data
}

export async function editQuery(username, token, query_data) {
    let data = {};
    query_data['username'] = username
    query_data['token'] = token
    let res = await fetch('/edit_query', {
                method: 'POST',
                body: JSON.stringify(query_data),
                })
    try {
        data = await res.json();
    } catch (error){
        console.error(error)
    }
    return data
}

export async function saveQuery(username, token) {
    let data = {};
    let res = await fetch('/save', {
                method: 'POST',
                body: JSON.stringify({'username': username, 'token': token}),
                })
    try {
        data = await res.json();
    } catch (error){
        console.error(error)
    }
    return data
}