def _cleanup_conn(conn):
    try:
        conn.socket.close()
    except OSError:
        pass
