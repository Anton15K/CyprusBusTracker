CREATE TABLE routes (
        route_id INTEGER NOT NULL,
        route_short_name VARCHAR(200) NOT NULL,
        route_long_name VARCHAR(200) NOT NULL,
        PRIMARY KEY (route_id),
        UNIQUE (route_id)
);


CREATE TABLE stops (
        stop_id INTEGER NOT NULL,
        stop_name VARCHAR(100) NOT NULL,
        stop_lat FLOAT NOT NULL,
        stop_lon FLOAT NOT NULL,
        zone_id INTEGER NOT NULL,
        PRIMARY KEY (stop_id)
);


CREATE TABLE added_trips (
        trip_id INTEGER NOT NULL,
        route_id INTEGER NOT NULL,
        start_time VARCHAR(200) NOT NULL,
        direction_id INTEGER NOT NULL,
        PRIMARY KEY (route_id, start_time, direction_id)
);


CREATE TABLE trips (
        trip_id INTEGER NOT NULL,
        route_id INTEGER NOT NULL,
        service_id INTEGER NOT NULL,
        direction_id INTEGER NOT NULL,
        trip_headsign VARCHAR(200) NOT NULL,
        PRIMARY KEY (trip_id),
        UNIQUE (trip_id),
        FOREIGN KEY(route_id) REFERENCES routes (route_id)
);

CREATE TABLE shapes (
        shape_id INTEGER NOT NULL,
        shape_pt_lat FLOAT NOT NULL,
        shape_pt_lon FLOAT NOT NULL,
        shape_pt_sequence INTEGER NOT NULL,
        PRIMARY KEY (shape_id, shape_pt_sequence),
        FOREIGN KEY(shape_id) REFERENCES routes (route_id)
);

CREATE TABLE stop_times (
        trip_id INTEGER NOT NULL,
        arrival_time INTEGER NOT NULL,
        departure_time INTEGER NOT NULL,
        stop_id INTEGER NOT NULL,
        stop_sequence INTEGER NOT NULL,
        PRIMARY KEY (trip_id, stop_sequence),
        FOREIGN KEY(trip_id) REFERENCES trips (trip_id) ON DELETE CASCADE,
        FOREIGN KEY(stop_id) REFERENCES stops (stop_id)
);

CREATE TABLE telegram_users (
        chat_id BIGINT NOT NULL,
        username VARCHAR,
        first_name VARCHAR,
        is_active BOOLEAN NOT NULL,
        created_at TIMESTAMP NOT NULL,
        PRIMARY KEY (chat_id),
        UNIQUE (chat_id)
);

CREATE TABLE telegram_otp (
        id SERIAL NOT NULL,
        chat_id BIGINT NOT NULL,
        otp_code VARCHAR NOT NULL,
        created_at TIMESTAMP NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        verified_at TIMESTAMP,
        is_used BOOLEAN NOT NULL,
        PRIMARY KEY (id),
        UNIQUE (id),
        FOREIGN KEY (chat_id) REFERENCES telegram_users (chat_id)
);

CREATE TABLE pending_web_sessions (
        token VARCHAR NOT NULL,
        chat_id BIGINT,
        created_at TIMESTAMP NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        PRIMARY KEY (token),
        UNIQUE (token),
        FOREIGN KEY (chat_id) REFERENCES telegram_users (chat_id)
);

CREATE TABLE notification_subscriptions (
        id SERIAL NOT NULL,
        chat_id BIGINT NOT NULL,
        stop_id VARCHAR NOT NULL,
        route_id VARCHAR NOT NULL,
        notify_minutes_before INTEGER NOT NULL,
        is_active BOOLEAN NOT NULL,
        created_at TIMESTAMP NOT NULL,
        FOREIGN KEY (chat_id) REFERENCES telegram_users (chat_id),
        PRIMARY KEY (id),
        UNIQUE (id)
);

CREATE TABLE notification_log (
        id SERIAL NOT NULL,
        subscription_id INTEGER NOT NULL,
        trip_id VARCHAR NOT NULL,
        service_date DATE NOT NULL,
        sent_at TIMESTAMP,
        status VARCHAR,
        PRIMARY KEY (id),
        UNIQUE (id),
        UNIQUE (subscription_id, trip_id, service_date)
);