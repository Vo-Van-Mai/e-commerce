import { Dimensions, FlatList, Image, RefreshControl, ScrollView, SectionList, StatusBar, StyleSheet, Switch, Text, View, Animated, TextComponent, SafeAreaView } from "react-native";
import MyStyle from "../../style/MyStyle";
import { useEffect, useState, useRef } from "react";
import { Button } from "react-native";
import { ActivityIndicator, TextInput, Title } from "react-native-paper";
import { Colors } from "react-native/Libraries/NewAppScreen";


export const Items = (props) => {
    return <Text> Hello {props.firstName} {props.lastName}! </Text>
}

const Home = () => {
    // const [cate, setCate] = useState([]);
    // const [course, setCourse] = useState([])
    // const [q, setQ] = useState(null);
    
    // const loadCate = async() => {
    //     let res = await fetch("https://thanhduong.pythonanywhere.com/categories/");
    //     let data = await res.json();
        
    //     setCate(data);

    // }

    // const loadCourse = async () => {
    //     let url = "https://thanhduong.pythonanywhere.com/courses/"
    //     if (q)
    //         url = `${url}?q=${q}`;
    //     console.info(url);
    //     let res = await fetch(url);
    //     let data = await res.json();

    //     setCourse(data.results);
    // }
    
    // useEffect(() => {
    //     loadCate();
    // }, []);

    // useEffect(() => {
    //     const t = setTimeout(() => loadCourse(), 500);
    //     return () => {
    //         clearTimeout(t);
    //     console.info("clear" + Math.random()); 
    //     }
    // }, [q]);

    // return (
    //     <View style={MyStyle.container}>
    //         {cate.map(c => <Text key={c.id} style={MyStyle.text}>{c.name}</Text>)}

    //         <View>
    //             <TextInput value={q} onChangeText={t => setQ(t)} placeholder="Tim kiem khoa hoc" style={{borderStyle: "solic", borderColor: "lightgreen", borderWidth:1}}></TextInput>
    //         </View>

    //         {course.map(c =>
    //             <View key={c.id} style={{flexDirection: "row", margin: 5}}> 
    //                 <Image source={{uri: c.image }} style={{width:80, height: 80}}></Image>
    //                 <Text style={{color: "red", fontSize: 22, fontWeight: "bold"}}>{c.subject}</Text>
    //             </View>
    //         )}
    //     </View>
    // );

    // // minh họa sử dụng scroll view
    // const [items, setItem] = useState(['item01', 'item02', 'item03', 'item04', 'item05', 'item06','item07','item08','item09','item10','item11','item12'])
    // const [refreshing, setRefreshing] = useState(false)
    // const addItem = () => {
    //     setRefreshing(true);
        
    //     setTimeout(() => {
    //         const item = `Item ${parseInt(Math.random()*100)}`;
    //         setItem([item, ...items]);
    //         setRefreshing(false);
    //     }, 1000)
    // }
    
    // return (
    //     <ScrollView refreshControl={<RefreshControl refreshing={refreshing} onRefresh={addItem} />}>
    //         {items.map(i => <Text style={styles.txt} key={i}>{i}</Text>)}
    //     </ScrollView>
    // );

    // // Minh hoa su dung flatlist
    // const [items, setItem] = useState(['item01', 'item02', 'item03', 'item04', 'item05', 'item06','item07','item08','item09','item10','item11','item12'])

    // const addItem = () => {
    //     let item = `Item ${parseInt(Math.random() * 100)}`;
    //     setItem([...items, item]);
    // }

    // return (
    //     <View>
    //         <FlatList onEndReached={addItem} data={items}
    //         renderItem={({item}) => <Text key={item} style={styles.txt}>{item}</Text>}/>
    //     </View>
    // );

//     // minh hoa switch, ActivityIndicator
//     const [background, setBackgound] = useState("white")
//     const [active, setActive] = useState(false);
//     const [color, setColor] = useState(null);
//     const [loading, setLoading] = useState(false);

//     const changeBackground = (t) => {
//         setActive(t);
//         if (t===true)
//             setBackgound("black");
//         else
//             setBackgound("white");
//     }

//     const changColor = () => {
//         setLoading(true);
//         const t = setTimeout(() => {
//             setBackgound(color);
//             setLoading(false);
//         }, 2000)
//     }



//     return (
//         <View style={{ flex: 1, backgroundColor: background}}>
//             <StatusBar />
//             <TextInput value={color} onChangeText={(t) => setColor(t)} placeholder="enter color ..." style={{borderStyle: "solic", borderColor: "red", borderWidth:1}}/>
//             <Button title="Change color" onPress={changColor}/>
//             { loading && <ActivityIndicator />}
//             <View style={{backgroundColor: background}}>
//                 <Switch value={active} onValueChange={t => changeBackground(t)} />
//             </View>
//         </View>
//     );
// }

    const textOpacity = useRef( new Animated.Value(0)).current;

    useEffect(() => {
        Animated.timing(textOpacity, {
            toValue: 1,
            duration: 2000,
            useNativeDriver: true
        }).start();
    }, [textOpacity]);

    return (
        <Animated.View style={{flex: 1, justifyContent: "center", alignItems: "center", opacity: textOpacity}}>
            <Text style={styles.header}>WELCOME!</Text>
        </Animated.View>
    );
}

export default Home;
const styles = StyleSheet.create({
    txt: {
        fontSize: 100,
        backgroundColor: "darkblue",
        marginTop: 5,
        color: "white"
    },
    header : {
        fontSize: 30,
        color: "blue",
        fontWeight: "bold"
    }
})