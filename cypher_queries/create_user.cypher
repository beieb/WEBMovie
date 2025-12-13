CREATE (u:USER {
    user_id: $user_id,
    pseudo: $pseudo,
    password: $password
})
RETURN u.user_id AS user_id
