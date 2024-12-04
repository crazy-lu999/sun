import os,time,re,sys
os.add_dll_directory(r'C:\PyCalmCar\dll')

import CalmCarLib.COM.DDS.fastdds as fastdds
from threading import Condition

# os.add_dll_directory(r'C:\SandBox\04_test\TestCases\IPC\idl')
# sys.path.append(r'C:\SandBox\04_test\TestCases\IPC\idl')
# import CarInfo as idl
idl = None


# @note WriterReaderBase\n 把 Writer Reader 共用的部分封装在该类下
class WriterReaderBase:
    dds_data_struct = None
    arr_index = re.compile('\[(\d{1,10})\]')
    def __init__(self, topic,topic_type):
        """
        @note 根据官方example修改，将 Writer Reader 共用部分提出来\n
        并且把 topic topic_type 通用化
        """
        domain = 0
        self.topic_name = topic
        self.topic_type = topic_type
        factory = fastdds.DomainParticipantFactory.get_instance()
        self.participant_qos = fastdds.DomainParticipantQos()
        factory.get_default_participant_qos(self.participant_qos)
        self.participant = factory.create_participant(domain, self.participant_qos)

        tmp = getattr(self.dds_data_struct, '%sPubSubType' % self.topic_type)
        self.topic_data_type = tmp()
        self.topic_data_type.setName("calmcar::msg::dds_::%s_" % self.topic_type)

        self.type_support = fastdds.TypeSupport(self.topic_data_type)
        self.participant.register_type(self.type_support)

        self.topic_qos = fastdds.TopicQos()
        self.participant.get_default_topic_qos(self.topic_qos)
        self.topic = self.participant.create_topic("rt/%s" % self.topic_name, self.topic_data_type.getName(), self.topic_qos)

    def translate(self,path):
        parsed_path = []
        elements = path.split('.')
        for el in elements:
            res = self.arr_index.findall(el)
            if len(res) > 0:
                parsed_path.append({'member': self.arr_index.sub('',el),'is_array':True,'index':int(res[0])})
            else:
                parsed_path.append({'member': el, 'is_array': False})
        return parsed_path


class WriterListener (fastdds.DataWriterListener) :
    def __init__(self, writer) :
        self._writer = writer
        super().__init__()

    def on_publication_matched(self, datawriter, info) :
        if (0 < info.current_count_change) :
            print ("Publisher matched subscriber {}".format(info.last_subscription_handle))
            self._writer._cvDiscovery.acquire()
            self._writer._matched_reader += 1
            self._writer._cvDiscovery.notify()
            self._writer._cvDiscovery.release()
        else :
            print ("Publisher unmatched subscriber {}".format(info.last_subscription_handle))
            self._writer._cvDiscovery.acquire()
            self._writer._matched_reader += 1
            self._writer._cvDiscovery.notify()
            self._writer._cvDiscovery.release()



class Writer(WriterReaderBase):
    def __init__(self):
        pass

    def init(self, topic,topic_type):
        self.machine = 0
        self._matched_reader = 0
        self._cvDiscovery = Condition()

        super().__init__(topic,topic_type)

        self.publisher_qos = fastdds.PublisherQos()
        self.participant.get_default_publisher_qos(self.publisher_qos)
        self.publisher = self.participant.create_publisher(self.publisher_qos)

        self.listener = WriterListener(self)
        self.writer_qos = fastdds.DataWriterQos()
        self.publisher.get_default_datawriter_qos(self.writer_qos)
        self.writer = self.publisher.create_datawriter(self.topic, self.writer_qos, self.listener)

        tmp = getattr(self.dds_data_struct, '%s' % self.topic_type)
        self.pub_data = tmp()

    # def pub(self,path,var):
    #     tmp = self.pub_data
    #     elements = path.split('.')
    #     if len(elements) == 1:
    #         pass
    #     elif len(elements) > 1:
    #         for el in elements[:-1]:
    #             tmp = getattr(tmp,el)
    #             tmp = tmp()
    #     tmp = getattr(tmp, elements[-1])
    #     tmp(var)
    #     return None

    def pub(self,path,var):
        tmp = self.pub_data
        elements = self.translate(path)
        if len(elements) == 1:
            pass
        elif len(elements) > 1:
            for el in elements[:-1]:

                tmp = getattr(tmp,el['member'])
                tmp = tmp()
                if el['is_array']:
                    tmp = tmp[el['index']]

        el = elements[-1]

        tmp = getattr(tmp, el['member'])
        if el['is_array']:
            tmp = tmp()
            tmp[el['index']] = var
        else:
            tmp(var)
        return None

    def pub_update(self):
        self.writer.write(self.pub_data)

    # def pub_raw_data(self,raw_data):
    #     self.pub_data = raw_data


    def __del__(self):
        factory = fastdds.DomainParticipantFactory.get_instance()
        self.participant.delete_contained_entities()
        factory.delete_participant(self.participant)

    def wait_discovery(self) :
        self._cvDiscovery.acquire()
        print ("Writer is waiting discovery...")
        self._cvDiscovery.wait_for(lambda : self._matched_reader != 0)
        self._cvDiscovery.release()
        print("Writer discovery finished...")



class ReaderListener(fastdds.DataReaderListener):
    last_data = None
    def __init__(self,dds_data_struct,topic_type):
        super().__init__()
        self.dds_data_struct = dds_data_struct
        self.topic_type = topic_type

    def on_data_available(self, reader):
        info = fastdds.SampleInfo()

        tmp = getattr(self.dds_data_struct, self.topic_type)
        data = tmp()

        reader.take_next_sample(data, info)
        self.last_data = data

        # print("Received {message} : {index}".format(message=data.message(), index=data.index()))

    def on_subscription_matched(self, datareader, info) :
        if (0 < info.current_count_change) :
            print ("Subscriber matched publisher {}".format(info.last_publication_handle))
        else :
            print ("Subscriber unmatched publisher {}".format(info.last_publication_handle))


class Reader(WriterReaderBase):
    def __init__(self):
        pass

    def init(self, topic,topic_type):
        super().__init__(topic,topic_type)

        self.subscriber_qos = fastdds.SubscriberQos()
        self.participant.get_default_subscriber_qos(self.subscriber_qos)
        self.subscriber = self.participant.create_subscriber(self.subscriber_qos)

        self.listener = ReaderListener(self.dds_data_struct,self.topic_type)
        self.reader_qos = fastdds.DataReaderQos()
        self.subscriber.get_default_datareader_qos(self.reader_qos)
        self.reader = self.subscriber.create_datareader(self.topic, self.reader_qos, self.listener)


    def get(self,path):
        data = self.listener.last_data

        if data is not None:
            tmp = data
            elements = self.translate(path)
            for el in elements:
                tmp = getattr(tmp,el['member'])
                tmp = tmp()
                if el['is_array']:
                    tmp = tmp[el['index']]

            return tmp
        else:
            return None

    # def get(self,path):
    #     data = self.listener.last_data
    #
    #     if data is not None:
    #         tmp = data
    #         elements = path.split('.')
    #         for el in elements:
    #             tmp = getattr(tmp,el)
    #             tmp = tmp()
    #
    #         return tmp
    #     else:
    #         return None
class dds_topics:
    pub_topic = {}
    sub_topic = {}
    dds_data_struct = idl
    def __init__(self):
        pass

    def init_pub_topic(self,topic,topic_type):
        tmp = Writer()
        tmp.dds_data_struct = self.dds_data_struct
        tmp.init(topic,topic_type)
        self.pub_topic[topic] = tmp

    def init_sub_topic(self,topic,topic_type):
        tmp = Reader()
        tmp.dds_data_struct = self.dds_data_struct
        tmp.init(topic,topic_type)
        self.sub_topic[topic] = tmp

    #dds.pub_topic['apa_pub1'].pub('epb.can_time',i)

    def write(self,path,var,update=False):
        tmp = path.split('.')
        topic = tmp[0]
        sub_path = '.'.join(tmp[1:])
        self.pub_topic[topic].pub(sub_path,var)
        if update:
            self.pub_topic[topic].pub_update()
    # def write_raw(self,topic,data):
    #     self.pub_topic[topic].pub_raw_data(data)

    def read(self,path):
        tmp = path.split('.')
        topic = tmp[0]
        sub_path = '.'.join(tmp[1:])
        res = self.sub_topic[topic].get(sub_path)
        return res
        # for i in range(100):
        #     if res is None:
        #         time.sleep(0.1)
        #     else:
        #         break
        # return res

    def read_topic(self,topic):
        res = self.sub_topic[topic].listener.last_data
        return res

    def pub_update(self):
        for el in self.pub_topic:
            self.pub_topic[el].pub_update()




class dds_topics_robot(dds_topics):
    dds_data_struct = idl

    def write(self,path,var,update=False):
        var = eval(var)
        super().write(path,var,update)

    def read(self,path):
        for i in range(10):
            res = super().read(path)
            if res is None:
                time.sleep(0.1)
            else:
                break
        return res

    def read_topic(self,topic):
        for i in range(10):
            res = super().read_topic(topic)
            if res is None:
                time.sleep(0.1)
            else:
                break
        return res
    
   


if __name__ == '__main__':

    # topic = {}
    #
    # for i in range(3):
    #     topic['car_%d' % i] = Writer('apa_pub%d'%i,'CarInfoH')
    #
    # for i in range(20):
    #     print(i)
    #
    #     for el in topic:
    #         topic[el].pub('gear.system_time',i)
    #         topic[el].pub('gear.can_time',i)
    #         topic[el].pub('epb.can_time',i)
    #         topic[el].pub_update()
    #         time.sleep(0.1)

    dds = dds_topics()

    # dds.init_sub_topic('apa_pub1','CarInfoH')
    # dds.init_sub_topic('apa_pub2','CarInfoL')
    #
    # dds.init_pub_topic('apa_pub1','CarInfoH')
    # dds.init_pub_topic('apa_pub2','CarInfoL')

    dds.init_sub_topic('car_info_h_pub','CarInfoH')

    # carh = Reader('apa_pub1','CarInfoH')
    # carl = Reader('apa_pub2','CarInfoL')
    #
    # CarInfoH = Writer('apa_pub1','CarInfoH')
    # CarInfoL = Writer('apa_pub2','CarInfoL')

    for i in range(100):
        # print(i)
        # dds.sub_topic['car_info_h_pub'].get('gear.system_time',i+1)
        # CarInfoH.pub('gear.system_time',i+1)
        # CarInfoH.pub('gear.can_time',i)
        # CarInfoH.pub('epb.can_time',i)
        # CarInfoH.pub_update()
        # CarInfoL.pub('body_info.can_time',i*5)
        # CarInfoL.pub_update()
        # print('sys',carh.get('gear.can_time'))
        # print('body_info',carl.get('body_info.can_time'))
        res = dds.sub_topic['car_info_h_pub'].get('gear.system_time')
        print(res)


        # dds.pub_update()
        time.sleep(0.1)
