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