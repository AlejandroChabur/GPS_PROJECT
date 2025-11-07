--
-- PostgreSQL database dump
--

\restrict MqGwRSy9d3h8EPGo9DhcZ3yxzR3bfgdgRCiTXCjBhQvjuy55BWcE7AfkEHiB3Q4

-- Dumped from database version 18.0
-- Dumped by pg_dump version 18.0

-- Started on 2025-11-06 22:52:22

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 2 (class 3079 OID 17612)
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- TOC entry 6025 (class 0 OID 0)
-- Dependencies: 2
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry and geography spatial types and functions';


--
-- TOC entry 861 (class 1255 OID 18852)
-- Name: generate_random_events(integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.generate_random_events(num_records integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
  i INT;
  v_vehicle INT;
  v_device INT;
  v_event INT;
  v_user INT;
  v_lat NUMERIC;
  v_lon NUMERIC;
BEGIN
  FOR i IN 1..num_records LOOP
    SELECT vehicle_id INTO v_vehicle FROM vehicle ORDER BY random() LIMIT 1;
    SELECT device_id INTO v_device FROM device ORDER BY random() LIMIT 1;
    SELECT event_id INTO v_event FROM event_type ORDER BY random() LIMIT 1;
    SELECT user_id INTO v_user FROM "user" WHERE is_active = TRUE ORDER BY random() LIMIT 1;
    
    v_lat := 4.60 + random()*0.1;
    v_lon := -74.10 + random()*0.1;
    
    INSERT INTO event_record (
      time_stamp_event, 
      vehicle_id, 
      device_id, 
      event_id, 
      user_id,
      geom, 
      speed, 
      angle, 
      satellites, 
      hdop, 
      pdop, 
      total_odometer
    ) VALUES (
      NOW() - (random()*10 || ' days')::interval,
      v_vehicle,
      v_device,
      v_event,
      v_user,
      ST_SetSRID(ST_MakePoint(v_lon, v_lat), 4326)::geography,
      (random()*100)::NUMERIC(5,2),
      (random()*360)::NUMERIC(6,2),
      (1 + floor(random()*12))::SMALLINT,
      (0.5 + random()*5)::NUMERIC(3,2),
      (1 + random()*5)::NUMERIC(3,2),
      (random()*100000)::NUMERIC(10,2)
    );
  END LOOP;
END;
$$;


ALTER FUNCTION public.generate_random_events(num_records integer) OWNER TO postgres;

--
-- TOC entry 285 (class 1255 OID 18795)
-- Name: update_timestamp(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_timestamp() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 226 (class 1259 OID 18695)
-- Name: company; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.company (
    company_id integer NOT NULL,
    company_name character varying(100) NOT NULL
);


ALTER TABLE public.company OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 18694)
-- Name: company_company_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.company_company_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.company_company_id_seq OWNER TO postgres;

--
-- TOC entry 6026 (class 0 OID 0)
-- Dependencies: 225
-- Name: company_company_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.company_company_id_seq OWNED BY public.company.company_id;


--
-- TOC entry 232 (class 1259 OID 18730)
-- Name: device; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.device (
    device_id integer NOT NULL,
    imei character varying(50) NOT NULL,
    manufacturer_id integer NOT NULL
);


ALTER TABLE public.device OWNER TO postgres;

--
-- TOC entry 231 (class 1259 OID 18729)
-- Name: device_device_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.device_device_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.device_device_id_seq OWNER TO postgres;

--
-- TOC entry 6027 (class 0 OID 0)
-- Dependencies: 231
-- Name: device_device_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.device_device_id_seq OWNED BY public.device.device_id;


--
-- TOC entry 236 (class 1259 OID 18764)
-- Name: event_record; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.event_record (
    record_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    deleted_at timestamp with time zone,
    ip character varying(50),
    time_stamp_event timestamp with time zone NOT NULL,
    user_id integer,
    location_desc character varying(150),
    geom public.geography(Point,4326),
    altitude numeric(8,2),
    angle numeric(6,2),
    satellites smallint,
    speed numeric(8,2),
    hdop numeric(5,2),
    pdop numeric(5,2),
    total_odometer numeric(10,2),
    reference_id character varying(100),
    vehicle_id integer NOT NULL,
    device_id integer NOT NULL,
    event_id integer NOT NULL,
    CONSTRAINT chk_valid_geom CHECK (((geom IS NULL) OR public.st_isvalid((geom)::public.geometry)))
);


ALTER TABLE public.event_record OWNER TO postgres;

--
-- TOC entry 235 (class 1259 OID 18763)
-- Name: event_record_record_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.event_record_record_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.event_record_record_id_seq OWNER TO postgres;

--
-- TOC entry 6028 (class 0 OID 0)
-- Dependencies: 235
-- Name: event_record_record_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.event_record_record_id_seq OWNED BY public.event_record.record_id;


--
-- TOC entry 230 (class 1259 OID 18717)
-- Name: event_type; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.event_type (
    event_id integer NOT NULL,
    event_name character varying(100) NOT NULL,
    properties jsonb
);


ALTER TABLE public.event_type OWNER TO postgres;

--
-- TOC entry 229 (class 1259 OID 18716)
-- Name: event_type_event_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.event_type_event_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.event_type_event_id_seq OWNER TO postgres;

--
-- TOC entry 6029 (class 0 OID 0)
-- Dependencies: 229
-- Name: event_type_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.event_type_event_id_seq OWNED BY public.event_type.event_id;


--
-- TOC entry 228 (class 1259 OID 18706)
-- Name: manufacturer; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.manufacturer (
    manufacturer_id integer NOT NULL,
    manufacturer_name character varying(100) NOT NULL
);


ALTER TABLE public.manufacturer OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 18705)
-- Name: manufacturer_manufacturer_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.manufacturer_manufacturer_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.manufacturer_manufacturer_id_seq OWNER TO postgres;

--
-- TOC entry 6030 (class 0 OID 0)
-- Dependencies: 227
-- Name: manufacturer_manufacturer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.manufacturer_manufacturer_id_seq OWNED BY public.manufacturer.manufacturer_id;


--
-- TOC entry 239 (class 1259 OID 18816)
-- Name: user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public."user" (
    user_id integer NOT NULL,
    username character varying(100) NOT NULL,
    email character varying(150) NOT NULL,
    full_name character varying(150),
    password_hash character varying(255),
    company_id integer,
    role character varying(50) DEFAULT 'operator'::character varying,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    is_active boolean DEFAULT true
);


ALTER TABLE public."user" OWNER TO postgres;

--
-- TOC entry 238 (class 1259 OID 18815)
-- Name: user_user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_user_id_seq OWNER TO postgres;

--
-- TOC entry 6031 (class 0 OID 0)
-- Dependencies: 238
-- Name: user_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_user_id_seq OWNED BY public."user".user_id;


--
-- TOC entry 234 (class 1259 OID 18747)
-- Name: vehicle; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vehicle (
    vehicle_id integer NOT NULL,
    plate character varying(20) NOT NULL,
    company_id integer NOT NULL
);


ALTER TABLE public.vehicle OWNER TO postgres;

--
-- TOC entry 233 (class 1259 OID 18746)
-- Name: vehicle_vehicle_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.vehicle_vehicle_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.vehicle_vehicle_id_seq OWNER TO postgres;

--
-- TOC entry 6032 (class 0 OID 0)
-- Dependencies: 233
-- Name: vehicle_vehicle_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.vehicle_vehicle_id_seq OWNED BY public.vehicle.vehicle_id;


--
-- TOC entry 237 (class 1259 OID 18797)
-- Name: vw_event_record_active; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_event_record_active AS
 SELECT record_id,
    created_at,
    updated_at,
    deleted_at,
    ip,
    time_stamp_event,
    user_id,
    location_desc,
    geom,
    altitude,
    angle,
    satellites,
    speed,
    hdop,
    pdop,
    total_odometer,
    reference_id,
    vehicle_id,
    device_id,
    event_id
   FROM public.event_record
  WHERE (deleted_at IS NULL);


ALTER VIEW public.vw_event_record_active OWNER TO postgres;

--
-- TOC entry 5805 (class 2604 OID 18698)
-- Name: company company_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company ALTER COLUMN company_id SET DEFAULT nextval('public.company_company_id_seq'::regclass);


--
-- TOC entry 5808 (class 2604 OID 18733)
-- Name: device device_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.device ALTER COLUMN device_id SET DEFAULT nextval('public.device_device_id_seq'::regclass);


--
-- TOC entry 5810 (class 2604 OID 18767)
-- Name: event_record record_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.event_record ALTER COLUMN record_id SET DEFAULT nextval('public.event_record_record_id_seq'::regclass);


--
-- TOC entry 5807 (class 2604 OID 18720)
-- Name: event_type event_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.event_type ALTER COLUMN event_id SET DEFAULT nextval('public.event_type_event_id_seq'::regclass);


--
-- TOC entry 5806 (class 2604 OID 18709)
-- Name: manufacturer manufacturer_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.manufacturer ALTER COLUMN manufacturer_id SET DEFAULT nextval('public.manufacturer_manufacturer_id_seq'::regclass);


--
-- TOC entry 5813 (class 2604 OID 18819)
-- Name: user user_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user" ALTER COLUMN user_id SET DEFAULT nextval('public.user_user_id_seq'::regclass);


--
-- TOC entry 5809 (class 2604 OID 18750)
-- Name: vehicle vehicle_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle ALTER COLUMN vehicle_id SET DEFAULT nextval('public.vehicle_vehicle_id_seq'::regclass);


--
-- TOC entry 5823 (class 2606 OID 18704)
-- Name: company company_company_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company
    ADD CONSTRAINT company_company_name_key UNIQUE (company_name);


--
-- TOC entry 5825 (class 2606 OID 18702)
-- Name: company company_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company
    ADD CONSTRAINT company_pkey PRIMARY KEY (company_id);


--
-- TOC entry 5835 (class 2606 OID 18740)
-- Name: device device_imei_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.device
    ADD CONSTRAINT device_imei_key UNIQUE (imei);


--
-- TOC entry 5837 (class 2606 OID 18738)
-- Name: device device_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.device
    ADD CONSTRAINT device_pkey PRIMARY KEY (device_id);


--
-- TOC entry 5845 (class 2606 OID 18779)
-- Name: event_record event_record_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.event_record
    ADD CONSTRAINT event_record_pkey PRIMARY KEY (record_id);


--
-- TOC entry 5831 (class 2606 OID 18728)
-- Name: event_type event_type_event_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.event_type
    ADD CONSTRAINT event_type_event_name_key UNIQUE (event_name);


--
-- TOC entry 5833 (class 2606 OID 18726)
-- Name: event_type event_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.event_type
    ADD CONSTRAINT event_type_pkey PRIMARY KEY (event_id);


--
-- TOC entry 5827 (class 2606 OID 18715)
-- Name: manufacturer manufacturer_manufacturer_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.manufacturer
    ADD CONSTRAINT manufacturer_manufacturer_name_key UNIQUE (manufacturer_name);


--
-- TOC entry 5829 (class 2606 OID 18713)
-- Name: manufacturer manufacturer_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.manufacturer
    ADD CONSTRAINT manufacturer_pkey PRIMARY KEY (manufacturer_id);


--
-- TOC entry 5853 (class 2606 OID 18834)
-- Name: user user_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_email_key UNIQUE (email);


--
-- TOC entry 5855 (class 2606 OID 18830)
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (user_id);


--
-- TOC entry 5857 (class 2606 OID 18832)
-- Name: user user_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_username_key UNIQUE (username);


--
-- TOC entry 5841 (class 2606 OID 18755)
-- Name: vehicle vehicle_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle
    ADD CONSTRAINT vehicle_pkey PRIMARY KEY (vehicle_id);


--
-- TOC entry 5843 (class 2606 OID 18757)
-- Name: vehicle vehicle_plate_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle
    ADD CONSTRAINT vehicle_plate_key UNIQUE (plate);


--
-- TOC entry 5838 (class 1259 OID 18806)
-- Name: idx_device_manufacturer; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_device_manufacturer ON public.device USING btree (manufacturer_id);


--
-- TOC entry 5846 (class 1259 OID 18801)
-- Name: idx_event_geom; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_event_geom ON public.event_record USING gist (geom);


--
-- TOC entry 5847 (class 1259 OID 18803)
-- Name: idx_event_speed; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_event_speed ON public.event_record USING btree (speed);


--
-- TOC entry 5848 (class 1259 OID 18802)
-- Name: idx_event_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_event_timestamp ON public.event_record USING btree (time_stamp_event);


--
-- TOC entry 5849 (class 1259 OID 18804)
-- Name: idx_event_vehicle_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_event_vehicle_time ON public.event_record USING btree (vehicle_id, time_stamp_event);


--
-- TOC entry 5850 (class 1259 OID 18840)
-- Name: idx_user_company; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_company ON public."user" USING btree (company_id);


--
-- TOC entry 5851 (class 1259 OID 18841)
-- Name: idx_user_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_username ON public."user" USING btree (username);


--
-- TOC entry 5839 (class 1259 OID 18805)
-- Name: idx_vehicle_company; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_vehicle_company ON public.vehicle USING btree (company_id);


--
-- TOC entry 5865 (class 2620 OID 18796)
-- Name: event_record trg_update_timestamp; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_update_timestamp BEFORE UPDATE ON public.event_record FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();


--
-- TOC entry 5866 (class 2620 OID 18842)
-- Name: user trg_user_update_timestamp; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_user_update_timestamp BEFORE UPDATE ON public."user" FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();


--
-- TOC entry 5858 (class 2606 OID 18741)
-- Name: device device_manufacturer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.device
    ADD CONSTRAINT device_manufacturer_id_fkey FOREIGN KEY (manufacturer_id) REFERENCES public.manufacturer(manufacturer_id);


--
-- TOC entry 5860 (class 2606 OID 18785)
-- Name: event_record event_record_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.event_record
    ADD CONSTRAINT event_record_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.device(device_id);


--
-- TOC entry 5861 (class 2606 OID 18790)
-- Name: event_record event_record_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.event_record
    ADD CONSTRAINT event_record_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.event_type(event_id);


--
-- TOC entry 5862 (class 2606 OID 18780)
-- Name: event_record event_record_vehicle_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.event_record
    ADD CONSTRAINT event_record_vehicle_id_fkey FOREIGN KEY (vehicle_id) REFERENCES public.vehicle(vehicle_id);


--
-- TOC entry 5863 (class 2606 OID 18843)
-- Name: event_record fk_event_user; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.event_record
    ADD CONSTRAINT fk_event_user FOREIGN KEY (user_id) REFERENCES public."user"(user_id);


--
-- TOC entry 5864 (class 2606 OID 18835)
-- Name: user user_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.company(company_id);


--
-- TOC entry 5859 (class 2606 OID 18758)
-- Name: vehicle vehicle_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle
    ADD CONSTRAINT vehicle_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.company(company_id);


-- Completed on 2025-11-06 22:52:22

--
-- PostgreSQL database dump complete
--

\unrestrict MqGwRSy9d3h8EPGo9DhcZ3yxzR3bfgdgRCiTXCjBhQvjuy55BWcE7AfkEHiB3Q4

